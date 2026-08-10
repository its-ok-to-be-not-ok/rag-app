#!/usr/bin/env python3
"""
Test Auto Schema Parser - Vector DB Output Format
"""

from ai.src.services.auto_schema_parser import AutoSchemaParser
from ai.src.services.schema_service import SchemaService

def test_vector_output():
    print("🔍 Auto Schema Parser - Vector DB Output Format")
    print("=" * 60)
    
    # Initialize services
    parser = AutoSchemaParser()
    schema_service = SchemaService()
    
    # Parse schema from JSON file
    print("📄 Parsing schema from schema.json...")
    db_schema = parser.parse_schema_file("schema.json")
    
    print(f"✅ Parsed {len(db_schema)} tables")
    print()
    
    # Test vector output format
    print("🔧 Testing Vector DB Output Format")
    print("-" * 40)
    
    sample_tables = list(db_schema.items())[:3]  # Take first 3 tables
    
    for table_name, info in sample_tables:
        print(f"📊 Table: {table_name}")
        print(f"   Full Name: {info.get('full_name', 'N/A')}")
        print(f"   Description: {info.get('description', 'N/A')}")
        print(f"   Columns Count: {len(info.get('columns', []))}")
        print(f"   Foreign Keys Count: {len(info.get('foreign_keys', []))}")
        
        # Generate chunk text (same as vector service)
        chunk_text = f"{table_name} {info.get('description', '')} {' '.join(info.get('columns', []))}"
        chunk_length = len(chunk_text)
        word_count = len(chunk_text.split())
        
        # Create chunk data in schema_chunks.json format
        chunk_data = {
            "table_name": table_name,
            "full_name": info.get('full_name', table_name),
            "description": info.get('description', ''),
            "columns": info.get('columns', []),
            "foreign_keys": info.get('foreign_keys', []),
            "chunk_text": chunk_text,
            "chunk_length": chunk_length,
            "word_count": word_count
        }
        
        print(f"   Chunk Text Length: {chunk_length}")
        print(f"   Word Count: {word_count}")
        print(f"   Chunk Preview: {chunk_text[:100]}...")
        print()
    
    # Test schema formatting
    print("📝 Schema Formatting Test")
    print("-" * 40)
    
    formatted_schema = schema_service.format_schema(db_schema)
    lines = formatted_schema.split('\n')
    
    print(f"Total lines: {len(lines)}")
    print(f"Total characters: {len(formatted_schema)}")
    print(f"Total words: {len(formatted_schema.split())}")
    print()
    
    # Show first few lines
    print("First 10 lines:")
    for i, line in enumerate(lines[:10]):
        print(f"{i+1:2d}: {line}")
    
    if len(lines) > 10:
        print(f"... and {len(lines) - 10} more lines")
    
    print()
    print("✅ Vector output format test completed!")
    
    # Test vector service integration
    print("\n🔗 Vector Service Integration Test")
    print("-" * 40)
    
    try:
        from ai.src.services.vector_service import VectorService
        
        vector_service = VectorService()
        print("✅ Vector service initialized successfully")
        
        # Test indexing (without actually indexing)
        print("📊 Schema structure for indexing:")
        print(f"   - Tables: {len(db_schema)}")
        print(f"   - Total columns: {sum(len(info.get('columns', [])) for info in db_schema.values())}")
        print(f"   - Total foreign keys: {sum(len(info.get('foreign_keys', [])) for info in db_schema.values())}")
        
        # Calculate estimated chunk sizes
        total_chunk_length = 0
        total_word_count = 0
        
        for table_name, info in db_schema.items():
            chunk_text = f"{table_name} {info.get('description', '')} {' '.join(info.get('columns', []))}"
            total_chunk_length += len(chunk_text)
            total_word_count += len(chunk_text.split())
        
        print(f"   - Total chunk length: {total_chunk_length:,} characters")
        print(f"   - Total word count: {total_word_count:,} words")
        print(f"   - Average chunk length: {total_chunk_length // len(db_schema):,} characters")
        print(f"   - Average word count: {total_word_count // len(db_schema):,} words")
        
    except Exception as e:
        print(f"❌ Vector service test failed: {e}")
    
    # Export to schema_chunks.json format
    print("\n💾 Exporting to schema_chunks.json format")
    print("-" * 40)
    
    import json
    
    all_chunks = []
    for table_name, info in db_schema.items():
        chunk_text = f"{table_name} {info.get('description', '')} {' '.join(info.get('columns', []))}"
        chunk_data = {
            "table_name": table_name,
            "full_name": info.get('full_name', table_name),
            "description": info.get('description', ''),
            "columns": info.get('columns', []),
            "foreign_keys": info.get('foreign_keys', []),
            "chunk_text": chunk_text,
            "chunk_length": len(chunk_text),
            "word_count": len(chunk_text.split())
        }
        all_chunks.append(chunk_data)
    
    # Save to file
    output_file = "schema_chunks_export.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Exported {len(all_chunks)} chunks to {output_file}")
    print(f"📊 Total size: {len(json.dumps(all_chunks)):,} characters")
    
    # Show sample
    print(f"\n📋 Sample chunk (first table):")
    sample = all_chunks[0]
    print(f"   Table: {sample['table_name']}")
    print(f"   Full Name: {sample['full_name']}")
    print(f"   Description: {sample['description']}")
    print(f"   Columns: {len(sample['columns'])}")
    print(f"   Foreign Keys: {len(sample['foreign_keys'])}")
    print(f"   Chunk Length: {sample['chunk_length']}")
    print(f"   Word Count: {sample['word_count']}")
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    test_vector_output()
