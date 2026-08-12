# 🚀 RAG Agentic Service & Schema Parser API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-1C1C1C?style=for-the-badge&logo=langchain)
![Qdrant](https://img.shields.io/badge/Qdrant-D33833?style=for-the-badge&logo=qdrant)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

A powerful Agentic RAG (Retrieval-Augmented Generation) service built with **FastAPI** and **LangGraph**. This application parses database schemas, indexes them into a **Qdrant Vector Database**, and intelligently generates precise SQL queries from natural language questions.

## ✨ Key Features

- 🧠 **Agentic Workflow (LangGraph):** Employs a stateful graph architecture to analyze schemas, retrieve historical query contexts, and generate accurate SQL queries.
- 📂 **Auto Schema Parsing:** Automatically extracts tables, columns, and foreign keys from JSON or PostgreSQL schema files.
- ⚡ **Adaptive Schema RAG:** If a database schema is too large (exceeds word threshold), the system automatically utilizes semantic vector search to retrieve only the most relevant tables.
- 🗄️ **Persistent Vector Storage:** Uses Qdrant to store schema chunks and similar historical queries for few-shot learning (Query RAG).
- 🔄 **Project Isolation:** Manages multiple schemas independently using isolated Qdrant collections (`project_id`).
- 📊 **Smart Suggestions:** Automatically suggests the most suitable chart type (Table, Bar, Line, etc.) alongside the generated SQL.

---

## 🏗️ Architecture

The system's core is driven by an adaptive **LangGraph** workflow (`SQLGeneratorGraph`):

1. **`retrieve_schema`** *(Conditional)*: Triggers if the database schema exceeds the token limit. Uses Qdrant to fetch the top N relevant tables based on the user's question.
2. **`analyze_schema`**: Uses an LLM to analyze relationships, suggest JOIN paths, identify primary/foreign keys, and formulate aggregation logic.
3. **`retrieve_rag`**: Searches Qdrant for historically similar questions and their correct SQL queries to provide few-shot examples.
4. **`generate_sql`**: Synthesizes the schema analysis, RAG context, and the user's question to produce the final SQL and chart suggestion.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Qdrant Vector Database (Local or Cloud)
- OpenAI API Key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/rag-app.git
   cd rag-app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables (`.env`):
   ```env
   LLM_MODEL=gpt-4o
   LLM_TEMPERATURE=0.0
   OPENAI_API_KEY=your_openai_api_key
   
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=your_qdrant_api_key
   QDRANT_COLLECTION=sql_queries
   
   SCHEMA_WORD_THRESHOLD=5000
   ```

4. Start the FastAPI Server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8045 --reload
   ```

---

## 🔌 API Reference

### 1. Upload Schema
Upload a JSON schema file to create a new project and index its vector embeddings.
- **POST** `/projects/upload-schema`
- **Body:** `multipart/form-data` (file: `schema.json`)

### 2. Generate SQL
Generate an SQL query from natural language.
- **POST** `/generate-sql`
- **Body:**
  ```json
  {
    "query": "Hiển thị tổng doanh thu theo từng tháng trong năm 2023",
    "project_id": "proj_123456789abc",
    "prompt_type": "generate_sql"
  }
  ```

### 3. Project Management
- **GET** `/projects` : List all active projects persisted in Qdrant.
- **GET** `/projects/{project_id}` : Get schema details of a specific project.
- **DELETE** `/projects/{project_id}` : Delete a project and its Qdrant collections.

### 4. Health Check
- **GET** `/health` : Returns system health status.

---

## 🛠️ Tech Stack Details
- **Core:** FastAPI, Pydantic, Python 3
- **LLM Orchestration:** LangChain, LangGraph, OpenAIEmbeddings, ChatOpenAI
- **Vector DB:** Qdrant Client
- **Parsing Tools:** Regular Expressions (Regex), Contextlib
