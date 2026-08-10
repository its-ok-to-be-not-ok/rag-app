from typing import Dict, List, Tuple, Union
import re
import json
from .auto_schema_parser import AutoSchemaParser


class SchemaService:
    def parse_postgresql_schema(self, schema_file_path: str) -> Dict:
        with open(schema_file_path, 'r') as f:
            content = f.read()
        
        tables = {}
        table_pattern = r'CREATE TABLE (\w+\.\w+)\s*\((.*?)\);'
        matches = re.finditer(table_pattern, content, re.DOTALL)
        
        for match in matches:
            table_full_name = match.group(1)
            table_name = table_full_name.split('.')[-1]
            table_body = match.group(2)
            
            columns = []
            foreign_keys = []
            
            for line in table_body.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                if 'REFERENCES' in line:
                    ref_match = re.search(r'REFERENCES\s+(\w+\.\w+)\((\w+)\)', line)
                    if ref_match:
                        ref_table = ref_match.group(1).split('.')[-1]
                        ref_column = ref_match.group(2)
                        col_name = line.split()[0]
                        foreign_keys.append(f"{col_name} -> {ref_table}.{ref_column}")
                
                col_match = re.match(r'(\w+)\s+', line)
                if col_match and not line.startswith('PRIMARY KEY') and not line.startswith('UNIQUE'):
                    columns.append(col_match.group(1))
            
            tables[table_name] = {
                "full_name": table_full_name,
                "columns": columns,
                "foreign_keys": foreign_keys,
                "description": self._get_table_description(table_name)
            }
        
        return tables
    
    def parse_json_schema(self, schema_file_path: str) -> Dict:
        parser = AutoSchemaParser()
        return parser.parse_schema_file(schema_file_path)
    
    def _get_table_description(self, table_name: str) -> str:
        words = re.split(r'[_\-\s]+', table_name.lower())
        words = [w for w in words if w and w not in ['core', 'public', 'private', 'dbo']]
        
        if not words:
            return f"Bảng {table_name}"
        
        readable_name = ' '.join(words)
        return f"Bảng {readable_name}"
    
    def format_schema(self, db_schema: Union[Dict, str]) -> str:
        if isinstance(db_schema, str):
            return db_schema
        
        return "\n".join([
            f"Table: {info.get('full_name', table)}\n"
            f"Columns: {', '.join(info['columns'])}\n"
            f"Description: {info.get('description', 'N/A')}"
            for table, info in db_schema.items()
        ])
    
    def get_table_details(self, db_schema: Union[Dict, str], table_names: List[str]) -> str:
        if isinstance(db_schema, str):
            lines = db_schema.strip().split('\n')
            details = []
            current_table = []
            in_target_table = False
            
            for line in lines:
                if line.startswith('Table:'):
                    if current_table and in_target_table:
                        details.append('\n'.join(current_table))
                    
                    table_name = line.split('Table:')[1].strip()
                    table_short = table_name.split('.')[-1] if '.' in table_name else table_name
                    in_target_table = any(t in table_name or t == table_short for t in table_names)
                    current_table = [line] if in_target_table else []
                elif in_target_table and line.strip():
                    current_table.append(line)
            
            if current_table and in_target_table:
                details.append('\n'.join(current_table))
            
            return '\n\n'.join(details) if details else db_schema
        
        details = []
        for table in table_names:
            if table in db_schema:
                info = db_schema[table]
                detail = f"Table: {info.get('full_name', table)}\n"
                detail += f"Columns: {', '.join(info['columns'])}\n"
                detail += f"Description: {info.get('description', 'N/A')}\n"
                
                if info.get('foreign_keys'):
                    detail += f"Foreign Keys: {', '.join(info['foreign_keys'])}\n"
                
                details.append(detail)
        
        return "\n".join(details)
    
    def parse_analysis_response(self, response: str) -> Tuple[List[str], str, str]:
        lines = response.split("\n")
        
        tables = []
        summary_lines = []
        notes_lines = []
        current_section = None
        
        for line in lines:
            if line.startswith("TABLES:"):
                tables = [t.strip() for t in line.replace("TABLES:", "").split(",")]
                current_section = "tables"
            elif line.startswith("SUMMARY:"):
                summary_lines.append(line.replace("SUMMARY:", "").strip())
                current_section = "summary"
            elif line.startswith("NOTES:"):
                notes_lines.append(line.replace("NOTES:", "").strip())
                current_section = "notes"
            elif line.strip() and current_section == "summary":
                summary_lines.append(line.strip())
            elif line.strip() and current_section == "notes":
                notes_lines.append(line.strip())
        
        summary = " ".join(summary_lines)
        notes = " ".join(notes_lines)
        
        return tables, summary, notes
    
    def parse_analysis_json(self, response: str) -> Dict:
        try:
            response_clean = response.strip()
            
            # Dùng Regex để tìm chính xác nội dung bên trong khối ```json ... ``` hoặc ``` ... ```
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_clean, re.DOTALL)
            if json_match:
                response_clean = json_match.group(1)
            else:
                # Tìm cặp ngoặc nhọn { ... } đầu tiên và cuối cùng trong chuỗi
                json_match_raw = re.search(r'(\{.*\})', response_clean, re.DOTALL)
                if json_match_raw:
                    response_clean = json_match_raw.group(1)
            
            analysis = json.loads(response_clean.strip())
            
            return {
                "tables": analysis.get("tables", []),
                "primary_columns": analysis.get("primary_columns", {}),
                "foreign_keys": analysis.get("foreign_keys", []),
                "join_paths": analysis.get("join_paths", []),
                "where_conditions": analysis.get("where_conditions", []),
                "order_by": analysis.get("order_by", []),
                "date_format": analysis.get("date_format", ""),
                "aggregation_logic": analysis.get("aggregation_logic", ""),
                "summary": analysis.get("summary", ""),
                "notes": analysis.get("notes", "")
            }
        except Exception as e:
            # Nếu parse vẫn thất bại, giữ lại thông tin thô để debug thay vì xóa sạch
            tables, summary, notes = self.parse_analysis_response(response)
            return {
                "tables": tables,
                "primary_columns": {},
                "foreign_keys": [],
                "join_paths": [],
                "where_conditions": [],
                "order_by": [],
                "date_format": "",
                "aggregation_logic": "",
                "summary": summary or response[:200],  # Lưu tạm 200 ký tự phản hồi để không bị rỗng
                "notes": notes or f"Parse JSON failed: {str(e)}"
            }

