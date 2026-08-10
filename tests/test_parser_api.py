#!/usr/bin/env python3
"""
Test script for Schema Parser API
"""

import requests
import json
import time
import os

API_BASE_URL = "http://localhost:8000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE = os.path.join(SCRIPT_DIR, "schema.json")

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\n🔍 Testing root endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
        return False

def test_parse_file():
    """Test file upload parsing"""
    print("\n🔍 Testing file upload parsing...")
    try:
        with open(SCHEMA_FILE, "rb") as f:
            files = {"file": ("schema.json", f, "application/json")}
            response = requests.post(f"{API_BASE_URL}/parse", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Parsed {data['metadata']['total_tables']} tables")
            print(f"📊 Metadata: {data['metadata']}")
            
            # Show first chunk
            if data['data']:
                first_chunk = data['data'][0]
                print(f"\n📋 First chunk sample:")
                print(f"   Table: {first_chunk['table_name']}")
                print(f"   Description: {first_chunk['description']}")
                print(f"   Columns: {len(first_chunk['columns'])}")
                print(f"   Chunk Length: {first_chunk['chunk_length']}")
                print(f"   Word Count: {first_chunk['word_count']}")
            
            return True
        else:
            print(f"❌ Parse failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
        return False

def test_parse_json_direct():
    """Test direct JSON parsing"""
    print("\n🔍 Testing direct JSON parsing...")
    try:
        with open(SCHEMA_FILE, "r") as f:
            schema_data = json.load(f)
        
        response = requests.post(
            f"{API_BASE_URL}/parse-json",
            json={"schema_data": schema_data},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Parsed {data['metadata']['total_tables']} tables")
            print(f"📊 Metadata: {data['metadata']}")
            return True
        else:
            print(f"❌ Parse failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Direct JSON test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Schema Parser API Tests")
    print("=" * 50)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(2)
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("File Upload Parse", test_parse_file),
        ("Direct JSON Parse", test_parse_json_direct)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")

if __name__ == "__main__":
    main()
