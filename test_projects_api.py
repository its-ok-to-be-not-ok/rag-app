#!/usr/bin/env python3
"""
Test script for Project Management API
"""
import requests
import json
from pathlib import Path

API_URL = "http://localhost:8045"

def test_upload_schema():
    """Test uploading schema to create a new project"""
    print("1. Upload Schema and Create Project:")
    
    schema_file = Path("tests/schema.json")
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return None
    
    with open(schema_file, 'rb') as f:
        files = {'file': ('schema.json', f, 'application/json')}
        response = requests.post(
            f"{API_URL}/projects/upload-schema",
            files=files
        )
    
    data = response.json()
    print(json.dumps(data, indent=2))
    
    project_id = data.get('project_id')
    print(f"✅ Project ID: {project_id}\n")
    return project_id

def test_list_projects():
    """Test listing all projects"""
    print("2. List All Projects:")
    
    response = requests.get(f"{API_URL}/projects")
    data = response.json()
    print(json.dumps(data, indent=2))
    print(f"✅ Total projects: {data.get('total_projects', 0)}\n")

def test_get_project(project_id):
    """Test getting project details"""
    print(f"3. Get Project Details ({project_id}):")
    
    response = requests.get(f"{API_URL}/projects/{project_id}")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ Tables: {len(data.get('tables', []))}\n")

def test_generate_sql(project_id):
    """Test generating SQL with project ID"""
    print(f"4. Generate SQL with Project ID ({project_id}):")
    
    response = requests.post(
        f"{API_URL}/generate-sql",
        json={
            "query": "Liệt kê tất cả projects",
            "project_id": project_id
        }
    )
    
    data = response.json()
    print(f"SQL: {data['sql']}")
    print(f"Chart: {data['suggested_chart_type']}")
    print(f"Project: {data['project_id']}")
    print(f"✅ SQL generated\n")

def test_add_example(project_id):
    """Test adding example query"""
    print(f"5. Add Example Query to Project ({project_id}):")
    
    response = requests.post(
        f"{API_URL}/add-example",
        json={
            "question": "Liệt kê tất cả projects",
            "sql": "SELECT id, display_name FROM public.project ORDER BY id ASC",
            "project_id": project_id
        }
    )
    
    data = response.json()
    print(json.dumps(data, indent=2))
    print("✅ Example added\n")

def test_generate_sql_with_rag(project_id):
    """Test generating SQL after adding example (should use RAG)"""
    print(f"6. Generate SQL After Adding Example ({project_id}):")
    
    response = requests.post(
        f"{API_URL}/generate-sql",
        json={
            "query": "Cho tôi xem danh sách projects",
            "project_id": project_id
        }
    )
    
    data = response.json()
    print(f"SQL: {data['sql']}")
    print(f"Similar queries: {data['metadata']['similar_queries_count']}")
    print(f"✅ SQL generated with RAG\n")

def test_delete_project(project_id):
    """Test deleting a project"""
    print(f"7. Delete Project ({project_id}):")
    
    response = requests.delete(f"{API_URL}/projects/{project_id}")
    data = response.json()
    print(json.dumps(data, indent=2))
    print("✅ Project deleted\n")

def test_verify_deletion(project_id):
    """Test that deleted project returns 404"""
    print(f"8. Verify Deletion ({project_id}):")
    
    response = requests.get(f"{API_URL}/projects/{project_id}")
    
    if response.status_code == 404:
        print(f"✅ Project not found (expected): {response.json()}\n")
    else:
        print(f"❌ Project still exists: {response.json()}\n")

def main():
    print("=== Test Project Management API ===\n")
    
    try:
        # Test workflow
        project_id = test_upload_schema()
        if not project_id:
            print("❌ Failed to create project")
            return
        
        test_list_projects()
        test_get_project(project_id)
        test_generate_sql(project_id)
        test_add_example(project_id)
        test_generate_sql_with_rag(project_id)
        test_delete_project(project_id)
        test_verify_deletion(project_id)
        
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

