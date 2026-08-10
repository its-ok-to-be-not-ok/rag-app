#!/bin/bash

API_URL="http://localhost:8045"

echo "=== Test Project Management API ==="
echo ""

# 1. Upload Schema
echo "1. Upload Schema and Create Project:"
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/projects/upload-schema" \
  -F "file=@tests/schema.json")
echo "$UPLOAD_RESPONSE" | python3 -m json.tool
PROJECT_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('project_id', ''))")
echo "Project ID: $PROJECT_ID"
echo ""

# 2. List Projects
echo "2. List All Projects:"
curl -s -X GET "$API_URL/projects" | python3 -m json.tool
echo ""

# 3. Get Project Details
echo "3. Get Project Details:"
curl -s -X GET "$API_URL/projects/$PROJECT_ID" | python3 -m json.tool
echo ""

# 4. Generate SQL with Project ID
echo "4. Generate SQL with Project ID:"
curl -s -X POST "$API_URL/generate-sql" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Liệt kê tất cả projects\",
    \"project_id\": \"$PROJECT_ID\",
    \"thread_id\": \"thread_test\"
  }" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"SQL: {data['sql']}\"); print(f\"Chart: {data['suggested_chart_type']}\"); print(f\"Project: {data['project_id']}\")"
echo ""

# 5. Add Example Query
echo "5. Add Example Query:"
curl -s -X POST "$API_URL/add-example" \
  -H "Content-Type: application/json" \
  -d "{
    \"question\": \"Liệt kê tất cả projects\",
    \"sql\": \"SELECT id, display_name FROM public.project ORDER BY id ASC\",
    \"project_id\": \"$PROJECT_ID\"
  }" | python3 -m json.tool
echo ""

# 6. Generate SQL after adding example (should use RAG)
echo "6. Generate SQL After Adding Example:"
curl -s -X POST "$API_URL/generate-sql" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Cho tôi xem danh sách projects\",
    \"project_id\": \"$PROJECT_ID\"
  }" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"SQL: {data['sql']}\"); print(f\"Similar queries: {data['metadata']['similar_queries_count']}\")"
echo ""

# 7. Delete Project
echo "7. Delete Project:"
curl -s -X DELETE "$API_URL/projects/$PROJECT_ID" | python3 -m json.tool
echo ""

# 8. Verify deletion
echo "8. Verify Deletion (should get 404):"
curl -s -X GET "$API_URL/projects/$PROJECT_ID" | python3 -m json.tool
echo ""

echo "✅ Test completed!"

