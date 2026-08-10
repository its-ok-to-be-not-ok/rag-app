# Changelog

## [Latest] - 2025-11-14

### ✨ Added
- **NEW API: POST /answer** - Answer general questions using LLM
  - Separate endpoint for Q&A without database context
  - Supports conversation history
  - No project_id required

### 🔄 Changed
- **Refactored API structure** - Separated SQL generation and general Q&A into distinct endpoints
  - `/generate-sql` - Only for SQL generation (requires project_id)
  - `/answer` - Only for general questions (no project_id needed)
  - Removed `mode` field from QueryRequest (cleaner API design)

### 📝 Updated
- Updated `QueryRequest` model - Removed mode field
- Created new `AnswerRequest` model for /answer endpoint
- Updated API documentation (API_EXAMPLES.md)
- Created new test files: `test_apis.py` and `test_apis.sh`
- Updated root endpoint (/) to reflect new API structure

### 🎯 Benefits
- **Better separation of concerns** - Each API has single responsibility
- **Easier to scale** - Can scale SQL and Q&A services independently
- **Cleaner API design** - No mode routing, more RESTful
- **Better developer experience** - Clear purpose for each endpoint

### 📊 API Comparison

| Feature | `/generate-sql` | `/answer` |
|---------|----------------|-----------|
| Purpose | Generate SQL | Answer questions |
| Requires Project | ✅ Yes | ❌ No |
| Database Access | ✅ Yes | ❌ No |
| Output | SQL + chart type | Text answer |
| Conversation | ✅ Yes | ✅ Yes |

### 🧪 Testing

```bash
# Test SQL API
curl -X POST "http://localhost:8045/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Liệt kê projects", "project_id": "proj_xxx"}'

# Test Answer API
curl -X POST "http://localhost:8045/answer" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python là gì?"}'
```

### 🔧 Migration Guide

If you're using the old API with `mode` field:

**Before:**
```json
{
  "query": "Python là gì?",
  "mode": "answer"
}
```

**After:**
```json
// Use dedicated /answer endpoint
POST /answer
{
  "query": "Python là gì?"
}
```

**Before:**
```json
{
  "query": "Liệt kê projects",
  "mode": "sql",
  "project_id": "proj_xxx"
}
```

**After:**
```json
// Use /generate-sql (mode field removed)
POST /generate-sql
{
  "query": "Liệt kê projects",
  "project_id": "proj_xxx"
}
```
