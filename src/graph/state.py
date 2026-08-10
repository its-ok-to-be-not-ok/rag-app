from typing import TypedDict, List, Optional, Dict


class GraphState(TypedDict):
    question: str
    use_schema_rag: bool
    schema_retrieval_results: List[dict]
    relevant_tables: List[str]
    schema_summary: str
    schema_analysis: Dict
    similar_queries: List[dict]
    google_search_results: List[dict]
    generated_sql: str
    error: Optional[str]
    timings_ms: List[dict]
    prompt_type: str 

