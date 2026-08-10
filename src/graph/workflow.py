from typing import Dict
from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import GraphNodes
from ..services.llm_service import LLMService
from ..services.vector_service import VectorService
from ..services.schema_service import SchemaService
from ..services.search_service import GoogleSearchService


class SQLGeneratorGraph:
    def __init__(self, db_schema: Dict, schema_word_threshold: int = 5000, project_id: str = None):
        self.db_schema = db_schema
        self.schema_word_threshold = schema_word_threshold
        self.project_id = project_id
        
        self.llm_service = LLMService()
        self.vector_service = VectorService(project_id=project_id)
        self.schema_service = SchemaService()
        self.search_service = GoogleSearchService()
        
        self.nodes = GraphNodes(
            db_schema=db_schema,
            llm_service=self.llm_service,
            vector_service=self.vector_service,
            schema_service=self.schema_service,
            search_service=self.search_service
        )
        
        self.use_schema_rag = self._should_use_schema_rag()
        self.graph = self._build_graph()
    
    def _should_use_schema_rag(self) -> bool:
        schema_text = self.schema_service.format_schema(self.db_schema)
        word_count = len(schema_text.split())
        print(f"Schema word count: {word_count}")
        print(f"Schema word threshold: {self.schema_word_threshold}")
        return word_count >= self.schema_word_threshold
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        
        workflow.add_node("analyze_schema", self.nodes.analyze_schema_node)
        workflow.add_node("retrieve_rag", self.nodes.retrieve_rag_node)
        # workflow.add_node("google_search", self.nodes.google_search_node)
        workflow.add_node("generate_sql", self.nodes.generate_sql_node)
        
        if self.use_schema_rag:
            workflow.add_node("retrieve_schema", self.nodes.retrieve_schema_node)
            workflow.set_entry_point("retrieve_schema")
            workflow.add_edge("retrieve_schema", "analyze_schema")
        else:
            workflow.set_entry_point("analyze_schema")
        
        workflow.add_edge("analyze_schema", "retrieve_rag")
        # workflow.add_edge("retrieve_rag", "google_search")
        # workflow.add_edge("google_search", "generate_sql")
        workflow.add_edge("retrieve_rag", "generate_sql")
        workflow.add_edge("generate_sql", END)
        
        return workflow.compile()
    
    def run(self, question: str, prompt_type: str = None) -> Dict:
        initial_state = {
            "question": question,
            "use_schema_rag": self.use_schema_rag,
            "schema_retrieval_results": [],
            "relevant_tables": [],
            "schema_summary": "",
            "schema_analysis": {},
            "similar_queries": [],
            "google_search_results": [],
            "generated_sql": "",
            "suggested_chart_type": "table",
            "error": None,
            "timings_ms": [],
            "prompt_type": prompt_type or "generate_sql"
        }
        
        result = self.graph.invoke(initial_state)
        return result
    
    def index_schema(self):
        self.vector_service.index_schema(self.db_schema)

