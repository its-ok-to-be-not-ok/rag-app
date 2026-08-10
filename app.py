from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from src.services.auto_schema_parser import AutoSchemaParser
from src.graph.workflow import SQLGeneratorGraph
from src.services.schema_service import SchemaService
from src.services.vector_service import VectorService
from src.config.settings import settings

# --- Logging setup ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(LOG_FORMAT))
handler.setLevel(LOG_LEVEL)

root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.addHandler(handler)

for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uvicorn_logger = logging.getLogger(uvicorn_logger_name)
    uvicorn_logger.handlers = [handler]
    uvicorn_logger.setLevel(LOG_LEVEL)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 [Startup] Đang quét qdrant_storage để load danh sách Project IDs vào Memory Cache...")
    try:
        vector_service = VectorService()
        existing_projects = vector_service.get_all_project_ids()
        app.state.existing_project_ids = set(existing_projects)
        print(f"✅ [Startup] Đã load {len(existing_projects)} projects: {existing_projects}")
    except Exception as e:
        print(f"⚠️ [Startup] Chưa thể kết nối Qdrant Storage: {e}")
        app.state.existing_project_ids = set()

    yield 

    app.state.existing_project_ids.clear()

app = FastAPI(
    title="RAG Agentic Service & Schema Parser API",
    description="Parse JSON schema files and convert to structured chunks",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = AutoSchemaParser()
schema_service = SchemaService()
projects: Dict[str, Dict] = {}

class QueryRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    prompt_type: Optional[str] = None

class SummarizeDataRequest(BaseModel):
    question: str
    sql_query: str
    data: Any
    project_id: Optional[str] = None


def restore_schema_from_qdrant(project_id: str) -> Dict[str, Any]:
    """Helper khôi phục lại db_schema từ Qdrant Payload khi RAM bị trống sau restart server"""
    db_schema = {}
    try:
        vector_service = VectorService(project_id=project_id)
        scroll_res = vector_service.client.scroll(
            collection_name=vector_service.schema_collection,
            limit=500,
            with_payload=True
        )
        points = scroll_res[0] if scroll_res else []
        
        for pt in points:
            payload = pt.payload or {}
            table_name = payload.get("table_name") or ""
            full_name = payload.get("full_name") or table_name
            short_name = table_name.split('.')[-1] if '.' in table_name else table_name
            
            if short_name:
                schema_entry = {
                    "short_name": short_name,
                    "full_name": full_name,
                    "description": payload.get("description", ""),
                    "columns": payload.get("columns", []),
                    "foreign_keys": payload.get("foreign_keys", [])
                }
                # Lưu BẮT BUỘC cả short_name và full_name để tránh lỗi lệch Key khi SchemaService lookup!
                db_schema[short_name] = schema_entry
                if full_name and full_name != short_name:
                    db_schema[full_name] = schema_entry

        logging.info(f"✅ [RESTORE SUCCESS] Đã khôi phục {len(db_schema)} bảng cho project '{project_id}': {list(db_schema.keys())}")
    except Exception as e:
        logging.warning(f"❌ [RESTORE FAILED] Lỗi khôi phục schema từ Qdrant cho '{project_id}': {e}")
        
    return db_schema


@app.get("/")
async def root():
    return {
        "message": "Schema Parser API",
        "version": "1.0.0",
        "endpoints": {
            "POST /projects/upload-schema": "Upload schema and create new project",
            "GET /projects": "List all project IDs",
            "GET /projects/{project_id}": "Get project details",
            "DELETE /projects/{project_id}": "Delete a project",
            "POST /generate-sql": "Generate SQL from natural language query",
            "GET /health": "Health check endpoint"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "schema-parser"}

@app.post("/projects/upload-schema")
async def upload_schema(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        content = await file.read()
        schema_data = json.loads(content.decode('utf-8'))
        
        db_schema = parser.parse_schema_data(schema_data)
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        
        sql_graph = SQLGeneratorGraph(
            db_schema=db_schema,
            schema_word_threshold=settings.SCHEMA_WORD_THRESHOLD,
            project_id=project_id
        )
        sql_graph.index_schema()
        
        projects[project_id] = {
            "schema": db_schema,
            "graph": sql_graph,
            "metadata": {
                "filename": file.filename,
                "total_tables": len(db_schema),
                "use_schema_rag": sql_graph.use_schema_rag,
                "schema_word_threshold": settings.SCHEMA_WORD_THRESHOLD,
                "created_at": str(uuid.uuid1().time)
            }
        }
        
        if hasattr(app.state, "existing_project_ids"):
            app.state.existing_project_ids.add(project_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "project_id": project_id,
                "schema_info": {
                    "filename": file.filename,
                    "total_tables": len(db_schema),
                    "use_schema_rag": sql_graph.use_schema_rag,
                    "schema_word_threshold": settings.SCHEMA_WORD_THRESHOLD
                }
            }
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload schema: {str(e)}")

@app.get("/projects")
async def list_projects():
    try:
        project_list = []
        # cached_ids = getattr(app.state, "existing_project_ids", set())
        
        # if not cached_ids:
        vector_service = VectorService()
        cached_ids = set(vector_service.get_all_project_ids())
        app.state.existing_project_ids = cached_ids

        for project_id in sorted(list(cached_ids)):
            metadata = projects.get(project_id, {}).get("metadata", {
                "source": "qdrant_storage",
                "status": "ready"
            })
            
            project_list.append({
                "project_id": project_id,
                "metadata": metadata
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "total_projects": len(project_list),
                "projects": project_list
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    try:
        cached_ids = getattr(app.state, "existing_project_ids", set())
        
        if project_id not in projects and project_id not in cached_ids:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        tables = []
        if project_id in projects:
            project_data = projects[project_id]
            db_schema = project_data["schema"]
            metadata = project_data["metadata"]
        else:
            metadata = {"source": "qdrant_storage", "status": "persisted_in_qdrant"}
            db_schema = restore_schema_from_qdrant(project_id)
        
        for table_name, info in db_schema.items():
            tables.append({
                "table_name": table_name,
                "full_name": info.get("full_name", table_name),
                "description": info.get("description", ""),
                "column_count": len(info.get("columns", [])),
                "foreign_key_count": len(info.get("foreign_keys", []))
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "project_id": project_id,
                "metadata": metadata,
                "tables": tables
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    try:
        try:
            vector_service = VectorService()
            vector_service.delete_project_collections(project_id)
        except Exception as ve:
            logging.warning(f"⚠️ Lỗi hoặc collection không tồn tại khi xóa {project_id}: {ve}")
        
        if project_id in projects:
            del projects[project_id]
        
        if hasattr(app.state, "existing_project_ids"):
            app.state.existing_project_ids.discard(project_id)
        
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": f"Project {project_id} deleted successfully"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


async def handle_sql_mode(request: QueryRequest):
    logging.info(f"[handle_sql_mode] Request: query={request.query}, project_id={request.project_id}")

    req_project_id = request.project_id

    if not req_project_id:
        raise HTTPException(status_code=400, detail="Missing project_id in request")

    # 1. Nếu project có trong RAM -> Lấy dùng ngay
    if req_project_id in projects:
        sql_graph = projects[req_project_id]["graph"]
        project_id = req_project_id
    else:
        logging.info(f"[handle_sql_mode] RAM rỗng. Đang thử khôi phục Schema từ Qdrant cho project_id: {req_project_id}")
        db_schema = restore_schema_from_qdrant(req_project_id)
        
        if db_schema:
            sql_graph = SQLGeneratorGraph(
                db_schema=db_schema,
                schema_word_threshold=settings.SCHEMA_WORD_THRESHOLD,
                project_id=req_project_id
            )
            projects[req_project_id] = {
                "schema": db_schema,
                "graph": sql_graph,
                "metadata": {"source": "qdrant_storage", "status": "restored"}
            }
            if hasattr(app.state, "existing_project_ids"):
                app.state.existing_project_ids.add(req_project_id)
            project_id = req_project_id
        else:
            # Nếu Qdrant thực sự không có data -> Trả 404 để NestJS bắt lỗi và tự re-upload
            logging.error(f"❌ Project {req_project_id} không có dữ liệu trên Qdrant.")
            raise HTTPException(
                status_code=404,
                detail=f"Project {req_project_id} not found in Qdrant storage."
            )

    logging.info(f"[handle_sql_mode] Bắt đầu sinh SQL cho query={request.query}")
    try:
        result = sql_graph.run(request.query, prompt_type=request.prompt_type)
        logging.info(f"[handle_sql_mode] Đã sinh SQL thành công: {result.get('generated_sql')}")
    except Exception as e:
        logging.error(f"[handle_sql_mode] Lỗi khi sinh SQL: {e}")
        raise

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "query": request.query,
            "project_id": project_id,
            "sql": result["generated_sql"],
            "suggested_chart_type": result.get("suggested_chart_type", "table"),
            "metadata": {
                "use_schema_rag": result.get("use_schema_rag", False),
                "relevant_tables": result.get("relevant_tables", []),
                "schema_analysis": result.get("schema_analysis", {})
            }
        }
    )

@app.post("/generate-sql")
async def generate_sql(request: QueryRequest):
    try:
        return await handle_sql_mode(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8045)