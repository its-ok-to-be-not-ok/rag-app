from typing import Dict
from datetime import datetime
from .state import GraphState
from ..services.llm_service import LLMService
from ..services.vector_service import VectorService
from ..services.schema_service import SchemaService
from ..services.search_service import GoogleSearchService
from ..services.prompt_service import PromptService


class GraphNodes:
    def __init__(
        self,
        db_schema: Dict,
        llm_service: LLMService,
        vector_service: VectorService,
        schema_service: SchemaService,
        search_service: GoogleSearchService
    ):
        self.db_schema = db_schema
        self.llm_service = llm_service
        self.vector_service = vector_service
        self.schema_service = schema_service
        self.search_service = search_service
        self.prompt_service = PromptService()
    
    def retrieve_schema_node(self, state: GraphState) -> GraphState:
        from time import perf_counter
        t0 = perf_counter()
        question = state["question"]
        
        relevant_tables = self.vector_service.search_relevant_tables(
            question=question,
            limit=5
        )
        
        state["schema_retrieval_results"] = relevant_tables
        state["relevant_tables"] = [t["table_name"] for t in relevant_tables]
        state.setdefault("timings_ms", []).append({"step": "retrieve_schema", "ms": int((perf_counter() - t0) * 1000)})
        return state
    
    def analyze_schema_node(self, state: GraphState) -> GraphState:
        from time import perf_counter
        t0 = perf_counter()
        question = state["question"]
        use_schema_rag = state["use_schema_rag"]
        
        if use_schema_rag:
            schema_retrieval_results = state["schema_retrieval_results"]
            relevant_tables = state["relevant_tables"]
            
            schema_context = self.schema_service.get_table_details(
                self.db_schema, 
                relevant_tables
            )
            
            retrieval_info = "\n".join([
                f"- {t['table_name']} (score: {t['score']:.3f}): {t['description']}"
                for t in schema_retrieval_results
            ])
            
            prompt = self.prompt_service.fill_prompt(
                "analyze_schema_with_rag",
                question=question,
                retrieval_info=retrieval_info,
                schema_context=schema_context
            )
        else:
            schema_context = self.schema_service.format_schema(self.db_schema)
            
            prompt = self.prompt_service.fill_prompt(
                "analyze_schema_full",
                question=question,
                schema_context=schema_context
            )
        
        response = self.llm_service.generate(prompt)
        
        analysis = self.schema_service.parse_analysis_json(response)
        
        if analysis["tables"]:
            state["relevant_tables"] = analysis["tables"]
        
        state["schema_summary"] = f"{analysis['summary']}\n\nLưu ý: {analysis['notes']}"
        state["schema_analysis"] = analysis
        state.setdefault("timings_ms", []).append({"step": "analyze_schema", "ms": int((perf_counter() - t0) * 1000)})
        return state
    
    def retrieve_rag_node(self, state: GraphState) -> GraphState:
        from time import perf_counter
        t0 = perf_counter()
        question = state["question"]
        
        similar_queries = self.vector_service.search_similar_queries(
            question=question,
            limit=10
        )
        
        state["similar_queries"] = similar_queries
        state.setdefault("timings_ms", []).append({"step": "retrieve_rag", "ms": int((perf_counter() - t0) * 1000)})
        return state
    
    def generate_sql_node(self, state: GraphState) -> GraphState:
        from time import perf_counter
        t0 = perf_counter()
        question = state["question"]
        schema_summary = state["schema_summary"]
        schema_analysis = state.get("schema_analysis", {})
        similar_queries = state["similar_queries"]
        relevant_tables = state["relevant_tables"]
        prompt_type = state.get("prompt_type", "generate_sql")
        
        similar_examples = self._format_similar_examples(similar_queries)
        table_schemas = self.schema_service.get_table_details(
            self.db_schema, 
            relevant_tables
        )
        
        analysis_context = self._format_schema_analysis(schema_analysis)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
        
        prompt = self.prompt_service.fill_prompt(
            prompt_type,
            question=question,
            current_time=current_time,
            table_schemas=table_schemas,
            schema_summary=schema_summary,
            analysis_context=analysis_context,
            similar_examples=similar_examples
        )
        
        response = self.llm_service.generate_json(prompt)
        
        sql = None
        chart_type = "table"
        try:
            import json
            data = json.loads(response.strip())
            sql = data.get("sql")
            chart_type = data.get("chart_type", "table")
        except Exception:
            sql = self._clean_sql_response(response)
            chart_type = self._suggest_chart_type(sql, question)
        
        state["generated_sql"] = sql or ""
        state["suggested_chart_type"] = chart_type
        state.setdefault("timings_ms", []).append({"step": "generate_sql", "ms": int((perf_counter() - t0) * 1000)})
        return state
    
    def _format_schema_analysis(self, analysis: dict) -> str:
        if not analysis:
            return ""
        
        parts = []
        
        if analysis.get("date_format"):
            parts.append(f"DATE FORMAT: {analysis['date_format']}")
        
        if analysis.get("aggregation_logic"):
            parts.append(f"AGGREGATION LOGIC: {analysis['aggregation_logic']}")
        
        if analysis.get("primary_columns"):
            parts.append("\nPrimary Columns:")
            for table, cols in analysis["primary_columns"].items():
                parts.append(f"  - {table}: {', '.join(cols)}")
        
        if analysis.get("foreign_keys"):
            parts.append("\nForeign Keys:")
            for fk in analysis["foreign_keys"]:
                parts.append(f"  - {fk.get('from')} -> {fk.get('to')} ({fk.get('relationship', 'unknown')})")
        
        if analysis.get("join_paths"):
            parts.append("\nSuggested JOIN Paths:")
            for path in analysis["join_paths"]:
                parts.append(f"  - {path}")
        
        if analysis.get("where_conditions"):
            parts.append("\nRecommended WHERE Conditions:")
            for cond in analysis["where_conditions"]:
                parts.append(f"  - {cond}")
        
        if analysis.get("order_by"):
            parts.append("\nSuggested ORDER BY:")
            for order in analysis["order_by"]:
                parts.append(f"  - {order}")
        
        if analysis.get("notes"):
            parts.append(f"\nIMPORTANT NOTES: {analysis['notes']}")
        
        return "\n".join(parts) if parts else ""
    
    def _format_similar_examples(self, similar_queries: list) -> str:
        if not similar_queries:
            return "Không có ví dụ tương tự"
        
        return "\n".join([
            f"Example {i+1} (relevance: {q['score']:.3f}):\n"
            f"Question: {q['question']}\n"
            f"SQL: {q['sql']}\n"
            for i, q in enumerate(similar_queries)
        ])
    
    
    def _clean_sql_response(self, response: str) -> str:
        sql = response.strip()
        
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").replace("```", "").strip()
        elif sql.startswith("```"):
            sql = sql.replace("```", "").strip()
        
        return sql

