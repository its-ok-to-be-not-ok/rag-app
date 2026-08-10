from typing import List, Dict
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from langchain_openai import OpenAIEmbeddings
from ..config.settings import settings


class VectorService:
    def __init__(self, project_id: str = None):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        )
        self.project_id = project_id
        if project_id:
            self.query_collection = f"{settings.QDRANT_COLLECTION}_{project_id}"
            self.schema_collection = f"{settings.QDRANT_COLLECTION}_schema_{project_id}"
        else:
            self.query_collection = settings.QDRANT_COLLECTION
            self.schema_collection = f"{settings.QDRANT_COLLECTION}_schema"
        
        embedding_key = settings.EMBEDDING_KEY if settings.EMBEDDING_KEY else settings.LLM_KEY
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=embedding_key
        )
        
        self._initialize_collections()
    
    def _initialize_collections(self):
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if self.query_collection not in collection_names:
            self.client.create_collection(
                collection_name=self.query_collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
        
        if self.schema_collection not in collection_names:
            self.client.create_collection(
                collection_name=self.schema_collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
    
    def search_similar_queries(self, question: str, limit: int = 10) -> List[Dict]:
        question_vector = self.embeddings.embed_query(question)

        # Fetch more results to improve diversity, then deduplicate by question
        fetch_limit = max(limit * 5, 10)
        search_result = self.client.search(
            collection_name=self.query_collection,
            query_vector=question_vector,
            limit=fetch_limit
        )

        seen_questions = set()
        deduped: List[Dict] = []
        for hit in search_result:
            q_text = hit.payload.get("question")
            if not q_text or q_text in seen_questions:
                continue
            seen_questions.add(q_text)
            deduped.append({
                "question": q_text,
                "sql": hit.payload.get("sql"),
                "score": hit.score
            })
            if len(deduped) >= limit:
                break

        return deduped
    
    def search_relevant_tables(self, question: str, limit: int = 5) -> List[Dict]:
        question_vector = self.embeddings.embed_query(question)

        # Fetch more and deduplicate by table_name to avoid repeated entries
        fetch_limit = max(limit * 5, 10)
        search_result = self.client.search(
            collection_name=self.schema_collection,
            query_vector=question_vector,
            limit=fetch_limit
        )

        seen_tables = set()
        deduped: List[Dict] = []
        for hit in search_result:
            table_name = hit.payload.get("table_name")
            if not table_name or table_name in seen_tables:
                continue
            seen_tables.add(table_name)
            deduped.append({
                "table_name": table_name,
                "description": hit.payload.get("description"),
                "columns": hit.payload.get("columns"),
                "foreign_keys": hit.payload.get("foreign_keys"),
                "score": hit.score
            })
            if len(deduped) >= limit:
                break

        return deduped
    
    def add_query(self, question: str, sql: str):
        vector = self.embeddings.embed_query(question)

        # Use deterministic ID to avoid duplicate inserts across runs
        stable_int_id = int(hashlib.md5(question.encode("utf-8")).hexdigest()[:12], 16)

        point = PointStruct(
            id=stable_int_id,
            vector=vector,
            payload={"question": question, "sql": sql}
        )

        self.client.upsert(
            collection_name=self.query_collection,
            points=[point]
        )
    
    def index_schema(self, db_schema):
        if isinstance(db_schema, str):
            points = []
            lines = db_schema.strip().split('\n')
            current_table = None
            current_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Table:'):
                    if current_table:
                        text = f"{current_table} {current_info.get('description', '')} {' '.join(current_info.get('columns', []))}"
                        vector = self.embeddings.embed_query(text)
                        stable_int_id = int(hashlib.md5(current_table.encode("utf-8")).hexdigest()[:12], 16)
                        point = PointStruct(
                            id=stable_int_id,
                            vector=vector,
                            payload={
                                **current_info,
                                "chunk_text": text,
                                "chunk_length": len(text),
                                "word_count": len(text.split())
                            }
                        )
                        points.append(point)
                    
                    full_table_name = line.split('Table:')[1].strip()
                    current_table = full_table_name.split('.')[-1] if '.' in full_table_name else full_table_name
                    current_info = {
                        "table_name": current_table,
                        "full_name": full_table_name,
                        "columns": [],
                        "foreign_keys": []
                    }
                
                elif line.startswith('Columns:'):
                    cols = line.split('Columns:')[1].strip().split(',')
                    current_info["columns"] = [c.strip() for c in cols]
                
                elif line.startswith('Description:'):
                    current_info["description"] = line.split('Description:')[1].strip()
                
                elif line.startswith('Foreign Keys:'):
                    fks = line.split('Foreign Keys:')[1].strip().split(',')
                    current_info["foreign_keys"] = [fk.strip() for fk in fks]
            
            if current_table:
                text = f"{current_table} {current_info.get('description', '')} {' '.join(current_info.get('columns', []))}"
                vector = self.embeddings.embed_query(text)
                stable_int_id = int(hashlib.md5(current_table.encode("utf-8")).hexdigest()[:12], 16)
                point = PointStruct(
                    id=stable_int_id,
                    vector=vector,
                    payload={
                        **current_info,
                        "chunk_text": text,
                        "chunk_length": len(text),
                        "word_count": len(text.split())
                    }
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.schema_collection,
                points=points
            )
        else:
            points = []
            for table_name, info in db_schema.items():
                text_for_embedding = f"{table_name} {info.get('description', '')} {' '.join(info.get('columns', []))}"
                vector = self.embeddings.embed_query(text_for_embedding)
                
                stable_int_id = int(hashlib.md5(table_name.encode("utf-8")).hexdigest()[:12], 16)
                point = PointStruct(
                    id=stable_int_id,
                    vector=vector,
                    payload={
                        "table_name": table_name,
                        "full_name": info.get("full_name", table_name),
                        "description": info.get("description", ""),
                        "columns": info.get("columns", []),
                        "foreign_keys": info.get("foreign_keys", []),
                        "chunk_text": text_for_embedding,
                        "chunk_length": len(text_for_embedding),
                        "word_count": len(text_for_embedding.split())
                    }
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.schema_collection,
                points=points
            )
    
    def clear_collections(self):
        """Clear all data from both collections"""
        try:
            self.client.delete_collection(self.query_collection)
            self.client.delete_collection(self.schema_collection)
            print("Cleared existing collections")
        except Exception as e:
            print(f"Error clearing collections: {e}")
        
        # Recreate collections
        self._initialize_collections()
        print("Recreated collections")
    
    def clear_query_collection(self):
        """Clear only the query collection"""
        try:
            self.client.delete_collection(self.query_collection)
            print("Cleared query collection")
        except Exception as e:
            print(f"Error clearing query collection: {e}")
        
        # Recreate collection
        self.client.create_collection(
            collection_name=self.query_collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        print("Recreated query collection")
    
    def clear_schema_collection(self):
        """Clear only the schema collection"""
        try:
            self.client.delete_collection(self.schema_collection)
            print("Cleared schema collection")
        except Exception as e:
            print(f"Error clearing schema collection: {e}")
        
        # Recreate collection
        self.client.create_collection(
            collection_name=self.schema_collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        print("Recreated schema collection")
    
    def get_all_project_ids(self) -> List[str]:
        """Get all project IDs from collections"""
        collections = self.client.get_collections().collections
        project_ids = set()
        
        base_name = settings.QDRANT_COLLECTION
        for col in collections:
            # Extract project_id from collection names like "queries_proj_xxx" or "queries_schema_proj_xxx"
            if col.name.startswith(f"{base_name}_") and not col.name.startswith(f"{base_name}_schema_"):
                # Format: queries_<project_id>
                project_id = col.name[len(base_name) + 1:]
                project_ids.add(project_id)
            elif col.name.startswith(f"{base_name}_schema_"):
                # Format: queries_schema_<project_id>
                project_id = col.name[len(f"{base_name}_schema_"):]
                project_ids.add(project_id)
        
        return sorted(list(project_ids))
    
    def delete_project_collections(self, project_id: str):
        """Delete all collections for a specific project"""
        query_collection = f"{settings.QDRANT_COLLECTION}_{project_id}"
        schema_collection = f"{settings.QDRANT_COLLECTION}_schema_{project_id}"
        
        try:
            self.client.delete_collection(query_collection)
            print(f"Deleted query collection for project {project_id}")
        except Exception as e:
            print(f"Error deleting query collection: {e}")
        
        try:
            self.client.delete_collection(schema_collection)
            print(f"Deleted schema collection for project {project_id}")
        except Exception as e:
            print(f"Error deleting schema collection: {e}")

