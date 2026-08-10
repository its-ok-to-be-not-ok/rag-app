from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import tempfile
import os
import uuid
from typing import List, Dict, Any, Optional
from src.services.auto_schema_parser import AutoSchemaParser
from src.graph.workflow import SQLGeneratorGraph
from src.services.schema_service import SchemaService
from src.services.vector_service import VectorService
from src.config.settings import settings
from contextlib import asynccontextmanager

# --- Logging setup: ensure logs always show in terminal, even with Uvicorn ---
import logging

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

# Remove all handlers associated with the root logger object (avoid duplicate logs)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(LOG_FORMAT))
handler.setLevel(LOG_LEVEL)

root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.addHandler(handler)

# Also patch uvicorn loggers to use the same handler/level
for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uvicorn_logger = logging.getLogger(uvicorn_logger_name)
    uvicorn_logger.handlers = [handler]
    uvicorn_logger.setLevel(LOG_LEVEL)

logging.getLogger().critical("TEST LOG: HELLO WORLD - NEU THAY DONG NAY THI LOGGING DA CHAY")

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 [Startup] Đang quét qdrant_storage để lưu danh sách Project IDs vào Memory Cache...")
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

# Store multiple projects: {project_id: {"schema": db_schema, "graph": sql_graph, "metadata": {...}}}
projects: Dict[str, Dict] = {}

class QueryRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    prompt_type: Optional[str] = None  # "generate_sql" or "generate_normal"
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Có bao nhiêu models trong project này?",
                "project_id": "proj_123",
                "prompt_type": "generate_normal"
            }
        }

class AnswerRequest(BaseModel):
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Python là gì?"
            }
        }

class SummarizeDataRequest(BaseModel):
    question: str
    sql_query: str
    data: Any
    project_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Find all jobs related to Python",
                "sql_query": "SELECT * FROM jobs WHERE tags ?| ARRAY['Python']",
                "data": [{"id": 1, "title": "Python Developer"}],
                "project_id": "proj_123"
            }
        }


def restore_schema_from_qdrant(project_id: str) -> Dict[str, Any]:
    """Helper khôi phục lại db_schema từ Qdrant Payload khi RAM bị trống sau restart server"""
    db_schema = {}
    try:
        vector_service = VectorService(project_id=project_id)
        scroll_res = vector_service.client.scroll(
            collection_name=vector_service.schema_collection,
            limit=200,
            with_payload=True
        )
        points = scroll_res[0] if scroll_res else []
        for pt in points:
            payload = pt.payload or {}
            t_name = payload.get("table_name") or payload.get("full_name")
            if t_name:
                db_schema[t_name] = {
                    "short_name": t_name,
                    "full_name": payload.get("full_name", t_name),
                    "description": payload.get("description", ""),
                    "columns": payload.get("columns", []),
                    "foreign_keys": payload.get("foreign_keys", [])
                }
    except Exception as e:
        logging.warning(f"[restore_schema_from_qdrant] Lỗi khôi phục schema cho {project_id}: {e}")
    return db_schema


@app.get("/")
async def root():
    return {
        "message": "Schema Parser API",
        "version": "1.0.0",
        "endpoints": {
            "POST /parse": "Upload JSON schema file and get parsed chunks",
            "POST /parse-json": "Parse JSON schema data directly",
            "POST /projects/upload-schema": "Upload schema and create new project",
            "GET /projects": "List all project IDs",
            "GET /projects/{project_id}": "Get project details",
            "DELETE /projects/{project_id}": "Delete a project",
            "POST /generate-sql": "Generate SQL from natural language query",
            "POST /answer": "Answer general questions using LLM",
            "POST /generate-chart": "Generate ECharts TypeScript code from data",
            "POST /add-example": "Add example query-sql pair for RAG",
            "GET /health": "Health check endpoint"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "schema-parser"}

@app.post("/projects/upload-schema")
async def upload_schema(file: UploadFile = File(...)):
    """
    Upload JSON schema file and create a new project
    """
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=400, 
                detail="Only JSON files are supported"
            )
        
        content = await file.read()
        schema_data = json.loads(content.decode('utf-8'))
        
        db_schema = parser.parse_schema_data(schema_data)
        
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        
        sql_graph = SQLGeneratorGraph(
            db_schema=db_schema,
            schema_word_threshold=settings.SCHEMA_WORD_THRESHOLD,
            project_id=project_id
        )
        
        if sql_graph.use_schema_rag:
            sql_graph.vector_service.clear_collections()
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
        
        # Cập nhật Cache Memory
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
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload schema: {str(e)}"
        )

@app.get("/projects")
async def list_projects():
    """
    List all project IDs from Vector DB / Cache
    """
    try:
        project_list = []
        cached_ids = getattr(app.state, "existing_project_ids", set())
        
        if not cached_ids:
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {str(e)}"
        )

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """
    Get detailed information about a specific project (lấy từ RAM hoặc tự khôi phục từ Qdrant Payload)
    """
    try:
        cached_ids = getattr(app.state, "existing_project_ids", set())
        
        if project_id not in projects and project_id not in cached_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found"
            )
        
        tables = []
        # 1. Trường hợp project còn trong RAM
        if project_id in projects:
            project_data = projects[project_id]
            db_schema = project_data["schema"]
            metadata = project_data["metadata"]
            
            for table_name, info in db_schema.items():
                tables.append({
                    "table_name": table_name,
                    "full_name": info.get("full_name", table_name),
                    "description": info.get("description", ""),
                    "column_count": len(info.get("columns", [])),
                    "foreign_key_count": len(info.get("foreign_keys", []))
                })
        else:
            # 2. Trường hợp RAM bị xóa do restart -> Khôi phục từ Qdrant Payload
            metadata = {
                "source": "qdrant_storage",
                "status": "persisted_in_qdrant"
            }
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project: {str(e)}"
        )

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and its associated vector collections safely
    """
    try:
        cached_ids = getattr(app.state, "existing_project_ids", set())
        
        # 1. Gọi VectorService xóa dữ liệu vật lý khỏi Qdrant (Bọc try-catch an toàn)
        try:
            # Khởi tạo VectorService không truyền project_id để tránh chạy _initialize_collections
            vector_service = VectorService()
            vector_service.delete_project_collections(project_id)
        except Exception as ve:
            logging.warning(f"⚠️ Lỗi hoặc collection không tồn tại trên Qdrant khi xóa {project_id}: {ve}")
        
        # 2. Xóa khỏi RAM dict nếu có
        if project_id in projects:
            del projects[project_id]
        
        # 3. Xóa khỏi In-Memory Cache của FastAPI
        if hasattr(app.state, "existing_project_ids"):
            app.state.existing_project_ids.discard(project_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Project {project_id} deleted successfully"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project: {str(e)}"
        )


async def handle_sql_mode(request: QueryRequest):
    """Handle SQL mode - Generate SQL from natural language"""
    logging.info(f"[handle_sql_mode] Nhận request: query={request.query}, project_id={request.project_id}, prompt_type={request.prompt_type}")

    cached_ids = getattr(app.state, "existing_project_ids", set())
    req_project_id = request.project_id

    # 1. Kiểm tra tồn tại
    if req_project_id and req_project_id not in cached_ids and req_project_id not in projects:
        logging.warning(f"[handle_sql_mode] Project_id {req_project_id} không tồn tại!")
        raise HTTPException(
            status_code=404,
            detail=f"Project {req_project_id} not found. Please upload schema first using /projects/upload-schema"
        )

    # 2. Lấy hoặc Tự khôi phục SQLGeneratorGraph
    if req_project_id and req_project_id in projects:
        project_data = projects[req_project_id]
        sql_graph = project_data["graph"]
        project_id = req_project_id
    elif req_project_id and req_project_id in cached_ids:
        # Tự động dựng lại SQLGeneratorGraph từ Qdrant Payload khi server từng bị restart
        logging.info(f"[handle_sql_mode] Khôi phục SQLGeneratorGraph từ Qdrant cho project_id: {req_project_id}")
        db_schema = restore_schema_from_qdrant(req_project_id)
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
        project_id = req_project_id
    else:
        # Fallback nếu không truyền project_id
        if not projects:
            logging.info("[handle_sql_mode] Không có project nào trong bộ nhớ, sẽ load schema mặc định.")
            db_schema = schema_service.parse_json_schema("tests/schema.json")
            project_id = "default"
            
            sql_graph = SQLGeneratorGraph(
                db_schema=db_schema,
                schema_word_threshold=settings.SCHEMA_WORD_THRESHOLD,
                project_id=project_id
            )
            
            if sql_graph.use_schema_rag:
                sql_graph.vector_service.clear_collections()
                sql_graph.index_schema()
            
            projects[project_id] = {
                "schema": db_schema,
                "graph": sql_graph,
                "metadata": {
                    "filename": "tests/schema.json",
                    "total_tables": len(db_schema),
                    "use_schema_rag": sql_graph.use_schema_rag,
                    "schema_word_threshold": settings.SCHEMA_WORD_THRESHOLD
                }
            }
            if hasattr(app.state, "existing_project_ids"):
                app.state.existing_project_ids.add(project_id)
        else:
            project_id = list(projects.keys())[0]
            logging.info(f"[handle_sql_mode] Không có project_id, lấy project đầu tiên: {project_id}")
            sql_graph = projects[project_id]["graph"]

    logging.info(f"[handle_sql_mode] Bắt đầu sinh SQL với sql_graph.run, query={request.query}")
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
                "schema_analysis": result.get("schema_analysis", {}),
                "similar_queries_count": len(result.get("similar_queries", [])),
                "timings_ms": result.get("timings_ms", [])
            }
        }
    )

@app.post("/generate-sql")
async def generate_sql(request: QueryRequest):
    logging.info("==> /generate-sql endpoint called")
    try:
        return await handle_sql_mode(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SQL: {str(e)}"
        )


@app.post("/summarize-data")
async def summarize_data(request: SummarizeDataRequest):
    try:
        from src.services.llm_service import LLMService
        import json
        
        llm_service = LLMService()
        
        prompt_path = "src/prompts/summarize_data.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        
        data_str = json.dumps(request.data, ensure_ascii=False, default=str)
        if len(data_str) > 10000:
            data_str = data_str[:10000] + "... (truncated)"
        
        prompt = prompt_template.format(
            question=request.question,
            sql_query=request.sql_query,
            data=data_str
        )
        
        response = llm_service.generate_json(prompt)
        
        try:
            summary_result = json.loads(response)
        except json.JSONDecodeError:
            summary_result = {
                "summary": response,
                "key_insights": [],
                "total_records": len(request.data) if isinstance(request.data, list) else 1,
                "has_data": bool(request.data)
            }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "question": request.question,
                "sql_query": request.sql_query,
                "project_id": request.project_id,
                "summary": summary_result.get("summary", ""),
                "key_insights": summary_result.get("key_insights", []),
                "total_records": summary_result.get("total_records", 0),
                "has_data": summary_result.get("has_data", False)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to summarize data: {str(e)}"
        )


class ExampleQueryRequest(BaseModel):
    question: str
    sql: str
    project_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Liệt kê tất cả projects",
                "sql": "SELECT id, display_name FROM public.project",
                "project_id": "proj_123"
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8045)