#!/bin/bash

API_URL="http://localhost:8045"

echo "=== Docker API Test Suite ==="
echo ""

echo "1. Health Check:"
curl -s ${API_URL}/health | python3 -m json.tool
echo ""

echo "2. Table Chart Test:"
curl -s -X POST "${API_URL}/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Liệt kê projects"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Chart: {d['suggested_chart_type']}\nSQL: {d['sql']}\")"
echo ""

echo "3. Bar Chart Test:"
curl -s -X POST "${API_URL}/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Đếm models theo project"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Chart: {d['suggested_chart_type']}\nSQL: {d['sql']}\")"
echo ""

echo "4. Number Chart Test:"
curl -s -X POST "${API_URL}/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Tổng số projects"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Chart: {d['suggested_chart_type']}\nSQL: {d['sql']}\")"
echo ""

echo "=== Conversation Flow Test ==="
echo ""

echo "5. Turn 1 - Initial Query:"
curl -s -X POST "${API_URL}/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Liệt kê tất cả projects",
    "project_id": "proj_test",
    "thread_id": "thread_test"
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Project: {d.get('project_id', 'N/A')}\nThread: {d.get('thread_id', 'N/A')}\nSQL: {d['sql'][:80]}...\nChart: {d['suggested_chart_type']}\nTurns: {d['metadata']['conversation_turns']}\")"
echo ""

echo "6. Turn 2 - With Context:"
curl -s -X POST "${API_URL}/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Chỉ lấy project có id = 1",
    "project_id": "proj_test",
    "thread_id": "thread_test",
    "conversation_history": [
      {"role": "user", "content": "Liệt kê tất cả projects"},
      {"role": "assistant", "content": "SELECT id, display_name FROM public.project"}
    ]
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"SQL: {d['sql'][:80]}...\nChart: {d['suggested_chart_type']}\nTurns: {d['metadata']['conversation_turns']}\")"
echo ""

echo "7. Turn 3 - Context-aware Query:"
curl -s -X POST "${API_URL}/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Có bao nhiêu models trong project đó?",
    "project_id": "proj_test",
    "thread_id": "thread_test",
    "conversation_history": [
      {"role": "user", "content": "Liệt kê tất cả projects"},
      {"role": "assistant", "content": "SELECT id, display_name FROM public.project"},
      {"role": "user", "content": "Chỉ lấy project có id = 1"},
      {"role": "assistant", "content": "SELECT id, display_name FROM public.project WHERE id = 1"}
    ]
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"SQL: {d['sql'][:80]}...\nChart: {d['suggested_chart_type']}\nTurns: {d['metadata']['conversation_turns']}\")"
echo ""

echo "✅ All tests completed!"
