from ai.src.graph import SQLGeneratorGraph
from ai.src.services.schema_service import SchemaService

schema_service = SchemaService()
db_schema = schema_service.parse_json_schema("tests/schema.json")

graph = SQLGeneratorGraph(db_schema=db_schema, schema_word_threshold=500)

print(f"Schema size: {len(schema_service.format_schema(db_schema).split())} words")
print(f"Number of tables: {len(db_schema)}")
print(f"Use Schema RAG: {graph.use_schema_rag}")

if graph.use_schema_rag:
    print("\nClearing old vector data...")
    graph.vector_service.clear_collections()
    print("\nIndexing schema vào vector database...")
    graph.index_schema()
else:
    print("\nSchema nhỏ, sẽ dùng toàn bộ schema trong prompt")

graph.add_example_query(
    question="Liệt kê tất cả projects",
    sql="SELECT id, display_name, type, catalog, created_at FROM public.project ORDER BY created_at DESC"
)

graph.add_example_query(
    question="Tìm models thuộc project có id = 1",
    sql="SELECT id, display_name, source_table_name, reference_name FROM public.model WHERE project_id = 1"
)

graph.add_example_query(
    question="Đếm số columns theo từng model",
    sql="SELECT m.reference_name, COUNT(mc.id) as column_count FROM public.model m LEFT JOIN public.model_column mc ON m.id = mc.model_id GROUP BY m.id, m.reference_name ORDER BY column_count DESC"
)

graph.add_example_query(
    question="Tìm các relations giữa models",
    sql="SELECT r.name, r.join_type, fc.reference_name as from_column, tc.reference_name as to_column FROM public.relation r JOIN public.model_column fc ON r.from_column_id = fc.id JOIN public.model_column tc ON r.to_column_id = tc.id"
)

graph.add_example_query(
    question="Liệt kê thread và số lượng responses",
    sql="SELECT t.id, t.summary, COUNT(tr.id) as response_count FROM public.thread t LEFT JOIN public.thread_response tr ON t.id = tr.thread_id GROUP BY t.id, t.summary ORDER BY t.created_at DESC"
)

graph.add_example_query(
    question="Top 10 câu hỏi gần nhất trong thread_response",
    sql="SELECT tr.id, tr.question, tr.sql, tr.created_at FROM public.thread_response tr ORDER BY tr.created_at DESC LIMIT 10"
)

graph.add_example_query(
    question="Tìm dashboards có nhiều items nhất",
    sql="SELECT d.id, d.name, COUNT(di.id) as item_count FROM public.dashboard d LEFT JOIN public.dashboard_item di ON d.id = di.dashboard_id GROUP BY d.id, d.name ORDER BY item_count DESC LIMIT 5"
)

graph.add_example_query(
    question="Metrics của từng project",
    sql="SELECT p.display_name, COUNT(m.id) as metric_count FROM public.project p LEFT JOIN public.metric m ON p.id = m.project_id GROUP BY p.id, p.display_name"
)

graph.add_example_query(
    question="SQL pairs cho training",
    sql="SELECT sp.question, sp.sql, p.display_name as project_name FROM public.sql_pair sp JOIN public.project p ON sp.project_id = p.id ORDER BY sp.created_at DESC LIMIT 20"
)

graph.add_example_query(
    question="Views đang active trong hệ thống",
    sql="SELECT v.id, v.name, v.statement, p.display_name as project FROM public.view v JOIN public.project p ON v.project_id = p.id WHERE v.cached = true"
)

graph.add_example_query(
    question="Deploy logs gần đây nhất",
    sql="SELECT dl.id, p.display_name, dl.status, dl.error, dl.created_at FROM public.deploy_log dl JOIN public.project p ON dl.project_id = p.id ORDER BY dl.created_at DESC LIMIT 10"
)

graph.add_example_query(
    question="API history theo project trong 24h qua",
    sql="SELECT p.display_name, COUNT(ah.id) as api_calls, AVG(ah.duration_ms) as avg_duration FROM public.api_history ah JOIN public.project p ON ah.project_id = p.id WHERE ah.created_at >= NOW() - INTERVAL '24 hours' GROUP BY p.id, p.display_name ORDER BY api_calls DESC"
)

graph.add_example_query(
    question="Instructions mặc định của các projects",
    sql="SELECT p.display_name, i.instruction, i.questions FROM public.instruction i JOIN public.project p ON i.project_id = p.id WHERE i.is_default = true"
)

graph.add_example_query(
    question="Dashboard refresh jobs đang chạy",
    sql="SELECT drj.hash, d.name as dashboard, di.display_name as item, drj.status, drj.started_at FROM public.dashboard_item_refresh_job drj JOIN public.dashboard d ON drj.dashboard_id = d.id JOIN public.dashboard_item di ON drj.dashboard_item_id = di.id WHERE drj.status = 'running'"
)

graph.add_example_query(
    question="Calculated columns trong models",
    sql="SELECT m.reference_name as model, mc.reference_name as column, mc.aggregation, mc.lineage FROM public.model_column mc JOIN public.model m ON mc.model_id = m.id WHERE mc.is_calculated = true"
)

question = "Tìm tất cả models và số lượng columns của chúng trong project có id = 1"
result = graph.run(question)

print(f"\n{'='*80}")
print(f"QUESTION: {result['question']}")
print(f"{'='*80}")

if result['use_schema_rag']:
    step_offset = 0
    print(f"\n{'─'*80}")
    print(f"STEP 1: RETRIEVE SCHEMA (RAG)")
    print(f"{'─'*80}")
    print(f"Retrieved {len(result['schema_retrieval_results'])} relevant tables:\n")
    for i, t in enumerate(result['schema_retrieval_results'], 1):
        print(f"{i}. {t['table_name']} (score: {t['score']:.4f})")
        print(f"   Description: {t['description']}")
        print(f"   Columns ({len(t['columns'])}): {', '.join(t['columns'])}")
        if t.get('foreign_keys'):
            print(f"   Foreign Keys: {', '.join(t['foreign_keys'])}")
        print()
else:
    step_offset = -1
    print(f"\n{'─'*80}")
    print(f"SKIP RETRIEVE SCHEMA (Schema < {graph.schema_word_threshold} words)")
    print(f"{'─'*80}")
    print("Using full schema for analysis\n")

print(f"{'─'*80}")
print(f"STEP {2 + step_offset}: ANALYZE SCHEMA")
print(f"{'─'*80}")
print(f"Relevant tables selected: {', '.join(result['relevant_tables'])}")
print(f"\nLLM Analysis:")
print(f"{result['schema_summary']}")
print()

print(f"{'─'*80}")
print(f"STEP {3 + step_offset}: RETRIEVE RAG (Similar Queries)")
print(f"{'─'*80}")
print(f"Retrieved {len(result['similar_queries'])} similar queries:\n")
for i, q in enumerate(result['similar_queries'], 1):
    print(f"{i}. Question: {q['question']}")
    print(f"   Score: {q['score']:.4f}")
    print(f"   SQL: {q['sql']}")
    print()

print(f"{'─'*80}")
print(f"STEP {4 + step_offset}: GENERATE SQL")
print(f"{'─'*80}")
print(f"\n{result['generated_sql']}\n")
print(f"Suggested Chart Type: {result.get('suggested_chart_type', 'table')}\n")

print(f"{'='*80}")
print("PERFORMANCE METRICS")
print(f"{'='*80}")
for t in result.get('timings_ms', []):
    step_name = t['step'].replace('_', ' ').title()
    bar_length = int(t['ms'] / 50)
    bar = '█' * bar_length
    print(f"{step_name:20s}: {t['ms']:5d} ms {bar}")

total_time = sum([t['ms'] for t in result.get('timings_ms', [])])
print(f"{'─'*80}")
print(f"{'TOTAL':20s}: {total_time:5d} ms")
print(f"{'='*80}")

