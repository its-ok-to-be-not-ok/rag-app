# 🚀 Dịch vụ RAG Agentic & API Phân Tích Schema

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-1C1C1C?style=for-the-badge&logo=langchain)
![Qdrant](https://img.shields.io/badge/Qdrant-D33833?style=for-the-badge&logo=qdrant)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

Một dịch vụ Agentic RAG (Retrieval-Augmented Generation) mạnh mẽ được xây dựng bằng **FastAPI** và **LangGraph**. Tác vụ này phân tích cấu trúc cơ sở dữ liệu (schema), đánh chỉ mục vào **Cơ sở dữ liệu Vector Qdrant**, và tự động tạo ra các câu truy vấn SQL chính xác từ câu hỏi ngôn ngữ tự nhiên.

## ✨ Tính Năng Chính

- 🧠 **Luồng Công Việc Agentic (LangGraph):** Sử dụng kiến trúc đồ thị có trạng thái (stateful graph) để phân tích schema, truy xuất ngữ cảnh các câu truy vấn lịch sử và tạo ra các câu lệnh SQL chính xác.
- 📂 **Tự Động Phân Tích Schema:** Tự động trích xuất các bảng, cột và khóa ngoại từ các tệp schema dạng JSON hoặc PostgreSQL.
- ⚡ **Adaptive Schema RAG:** Nếu schema của cơ sở dữ liệu quá lớn (vượt quá ngưỡng số từ quy định), hệ thống sẽ tự động sử dụng tìm kiếm vector ngữ nghĩa để chỉ lấy ra các bảng liên quan nhất.
- 🗄️ **Lưu Trữ Vector Lâu Dài:** Sử dụng Qdrant để lưu trữ các đoạn schema và các câu truy vấn lịch sử tương tự nhằm phục vụ việc học ít mẫu (Query RAG / Few-shot learning).
- 🔄 **Cô Lập Dự Án:** Quản lý nhiều schema độc lập bằng cách sử dụng các bộ sưu tập Qdrant riêng biệt (`project_id`).
- 📊 **Gợi Ý Thông Minh:** Tự động đề xuất loại biểu đồ phù hợp nhất (Bảng, Biểu đồ cột, Biểu đồ đường, v.v.) đi kèm với câu lệnh SQL được tạo ra.

---

## 🏗️ Kiến Trúc Hệ Thống

Cốt lõi của hệ thống được vận hành bởi luồng công việc **LangGraph** linh hoạt (`SQLGeneratorGraph`):

1. **`retrieve_schema`** *(Có điều kiện)*: Kích hoạt nếu schema cơ sở dữ liệu vượt quá giới hạn token. Sử dụng Qdrant để lấy ra N bảng liên quan nhất dựa trên câu hỏi của người dùng.
2. **`analyze_schema`**: Sử dụng LLM để phân tích mối quan hệ, gợi ý đường dẫn JOIN, xác định khóa chính/khóa ngoại và xây dựng logic gom nhóm dữ liệu (aggregation).
3. **`retrieve_rag`**: Tìm kiếm trong Qdrant các câu hỏi tương tự trong lịch sử cùng câu lệnh SQL đúng tương ứng để cung cấp các ví dụ mẫu (few-shot context).
4. **`generate_sql`**: Tổng hợp kết quả phân tích schema, ngữ cảnh RAG và câu hỏi của người dùng để tạo ra câu lệnh SQL cuối cùng cùng gợi ý biểu đồ.

---

## 🚀 Hướng Dẫn Bắt Đầu

### Yêu Cầu Tối Thiểu

- Python 3.9+
- Cơ sở dữ liệu Vector Qdrant (Cài đặt cục bộ hoặc Cloud)
- Mã khóa API của OpenAI (OpenAI API Key)

### Cài Đặt

1. Sao chép kho lưu trữ (Clone repository):
   ```bash
   git clone https://github.com/its-ok-to-be-not-ok/rag-app.git
   cd rag-app
   ```

2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```

3. Cấu hình Biến Môi Trường (`.env`):
   ```env
   LLM_MODEL=gpt-4o
   LLM_TEMPERATURE=0.0
   OPENAI_API_KEY=your_openai_api_key
   
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=your_qdrant_api_key
   QDRANT_COLLECTION=sql_queries
   
   SCHEMA_WORD_THRESHOLD=5000
   ```

4. Khởi chạy FastAPI Server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8045 --reload
   ```

---

## 🔄 Sơ Đồ Xử Lý Hệ Thống (Agentic Workflow)

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#333333',
    'lineColor': '#cccccc',
    'tertiaryColor': '#ffffff'
  },
  'flowchart': { 
    'nodeSpacing': 50, 
    'rankSpacing': 40
  }
}}%%
graph TD
    Start["🚀 Start:<br/>Nhận câu hỏi"]
    
    CheckSize["❓ Schema Word Count<br/>>= Threshold?"]
    
    RetrieveSchema["📂 1. Node: retrieve_schema<br/>
Tìm 5 bảng liên quan
qua Vector DB"]
    
    AnalyzeSchema["🧠 2. Node: analyze_schema<br/>
LLM phân tích JOIN paths"]
    
    RetrieveRAG["🗄️ 3. Node: retrieve_rag<br/>
Lấy các example SQL tương
tự trong Vector DB"]
    
    GenerateSQL["📊 4. Node: generate_sql<br/>
Sinh SQL & Chart Type"]
    
    End["🏁 End:<br/>
Trả về kết quả"]

    Start --> CheckSize
    CheckSize -->|"Có (Schema qua lon)"| RetrieveSchema
    RetrieveSchema --> AnalyzeSchema
    CheckSize -->|"Không (Schema nho)"| AnalyzeSchema
    
    AnalyzeSchema --> RetrieveRAG
    RetrieveRAG --> GenerateSQL
    GenerateSQL --> End

    classDef whiteNode fill:#ffffff,stroke:#333333,stroke-width:1.5px,color:#000000;

    class Start,End,RetrieveSchema,AnalyzeSchema,RetrieveRAG,GenerateSQL,CheckSize whiteNode;
  ```

### 3. Quản Lý Dự Án
- **GET** `/projects` : Liệt kê tất cả các dự án đang hoạt động được lưu trữ trong Qdrant.
- **GET** `/projects/{project_id}` : Lấy thông tin chi tiết về schema của một dự án cụ thể.
- **DELETE** `/projects/{project_id}` : Xóa một dự án và các bộ sưu tập dữ liệu liên quan trong Qdrant.

### 4. Kiểm Tra Trạng Thái (Health Check)
- **GET** `/health` : Trả về trạng thái hoạt động của hệ thống.

---

## 🛠️ Chi Tiết Công Nghệ Sử Dụng
- **Cốt lõi:** FastAPI, Pydantic, Python 3
- **Điều phối LLM:** LangChain, LangGraph, OpenAIEmbeddings, ChatOpenAI
- **Vector DB:** Qdrant Client
- **Công cụ Phân Tích:** Biểu thức chính quy (Regex), Contextlib
