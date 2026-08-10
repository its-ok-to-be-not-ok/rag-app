from typing import Dict, List, Any, Optional
import json
import re

class AutoSchemaParser:
    
    def parse_schema_file(self, file_path: str) -> Dict:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.parse_schema_data(data)
    
    def parse_schema_data(self, data: Any) -> Dict:
        if isinstance(data, list):
            return self._parse_array_schema(data)
        elif isinstance(data, dict):
            return self._parse_object_schema(data)
        else:
            raise ValueError("Schema must be either a list or dict")
    
    def _parse_array_schema(self, data: List[Dict]) -> Dict:
        tables = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            table_info = self._auto_extract_table(item)
            if table_info:
                tables[table_info['short_name']] = table_info
        return tables
    
    def _parse_object_schema(self, data: Dict) -> Dict:
        tables = {}
        for key, value in data.items():
            if isinstance(value, dict):
                table_info = self._auto_extract_table(value)
                if table_info:
                    tables[table_info['short_name']] = table_info
        return tables
    
    def _auto_extract_table(self, item: Dict) -> Optional[Dict]:
        table_name = self._find_table_name(item)
        if not table_name:
            return None
        
        table_short_name = self._extract_short_name(table_name)
        columns = self._auto_extract_columns(item)
        foreign_keys = self._auto_extract_foreign_keys(item)
        description = self._auto_generate_description(item, table_short_name)
        
        return {
            'short_name': table_short_name,
            'full_name': table_name,
            'columns': columns,
            'foreign_keys': foreign_keys,
            'description': description
        }
    
    def _find_table_name(self, item: Dict) -> Optional[str]:
        possible_keys = ['name', 'table_name', 'tableName', 'table', 'Table', 'NAME']
        for key in possible_keys:
            if key in item and item[key]:
                return str(item[key])
        
        if 'properties' in item and isinstance(item['properties'], dict):
            table_key = item['properties'].get('table') or item['properties'].get('tableName')
            if table_key:
                return str(table_key)
        
        return None
    
    def _extract_short_name(self, full_name: str) -> str:
        if '.' in full_name:
            return full_name.split('.')[-1]
        return full_name
    
    def _auto_extract_columns(self, item: Dict) -> List[str]:
        columns = []
        possible_keys = ['columns', 'fields', 'attributes', 'Columns', 'COLUMNS']
        
        columns_data = None
        for key in possible_keys:
            if key in item and isinstance(item[key], list):
                columns_data = item[key]
                break
        
        if not columns_data:
            return columns
        
        for col in columns_data:
            if isinstance(col, str):
                columns.append(col)
            elif isinstance(col, dict):
                col_str = self._format_column(col)
                if col_str:
                    columns.append(col_str)
        
        return columns
    
    def _format_column(self, col: Dict) -> Optional[str]:
        name_keys = ['name', 'column_name', 'columnName', 'field', 'fieldName']
        type_keys = ['type', 'dataType', 'data_type', 'columnType']
        desc_keys = ['description', 'desc', 'comment', 'remarks']
        
        col_name = None
        for key in name_keys:
            if key in col:
                col_name = col[key]
                break
        
        if not col_name:
            return None
        
        col_type = 'unknown'
        for key in type_keys:
            if key in col:
                col_type = col[key]
                break
        
        col_desc = None
        for key in desc_keys:
            if key in col and col[key]:
                col_desc = col[key]
                break
        
        if col_desc:
            return f"{col_name} ({col_type}): {col_desc}"
        else:
            return f"{col_name} ({col_type})"
    
    def _auto_extract_foreign_keys(self, item: Dict) -> List[str]:
        foreign_keys = []
        
        # 1. Đọc dạng mảng object 'foreignKeys' (system_schema.json)
        fk_list = item.get('foreignKeys') or item.get('foreign_keys') or item.get('relations')
        if isinstance(fk_list, list):
            for fk in fk_list:
                if isinstance(fk, dict):
                    from_col = fk.get('fromColumn') or fk.get('column')
                    to_table = fk.get('toTable') or fk.get('referenced_table')
                    to_col = fk.get('toColumn') or fk.get('referenced_column')
                    if from_col and to_table and to_col:
                        to_table_short = self._extract_short_name(to_table)
                        foreign_keys.append(f"{from_col} -> {to_table_short}.{to_col}")

        # 2. Đọc dạng mảng object 'constraint' (data_schema.json)
        constraints = item.get('constraint') or item.get('constraints')
        if isinstance(constraints, list):
            for c in constraints:
                if isinstance(c, dict):
                    c_type = str(c.get('constraintType', '')).upper()
                    if 'FOREIGN' in c_type or 'FK' in c_type:
                        fk_str = self._format_foreign_key(c)
                        if fk_str:
                            foreign_keys.append(fk_str)
                            
        return foreign_keys
    
    def _format_foreign_key(self, constraint: Dict) -> Optional[str]:
        col_keys = ['constraintColumn', 'column', 'from_column', 'fromColumn']
        ref_table_keys = ['constraintedTable', 'referenced_table', 'refTable', 'toTable']
        ref_col_keys = ['constraintedColumn', 'referenced_column', 'refColumn', 'toColumn']
        
        fk_col = None
        for key in col_keys:
            if key in constraint and constraint[key]:
                fk_col = constraint[key]
                break
        
        ref_table = None
        for key in ref_table_keys:
            if key in constraint and constraint[key]:
                ref_table = constraint[key]
                break
        
        ref_col = None
        for key in ref_col_keys:
            if key in constraint and constraint[key]:
                ref_col = constraint[key]
                break
        
        if fk_col and ref_table and ref_col:
            ref_table_short = self._extract_short_name(ref_table)
            return f"{fk_col} -> {ref_table_short}.{ref_col}"
        
        return None
    
    def _auto_generate_description(self, item: Dict, table_name: str) -> str:
        desc_keys = ['description', 'desc', 'comment', 'remarks', 'summary']
        for key in desc_keys:
            if key in item and item[key]:
                return str(item[key])
        return self._infer_description_from_name(table_name)
    
    def _infer_description_from_name(self, table_name: str) -> str:
        words = re.split(r'[_\-\s]+', table_name.lower())
        words = [w for w in words if w and w not in ['public', 'private', 'dbo']]
        if not words:
            return f"Bảng {table_name}"
        readable_name = ' '.join(words)
        return f"Bảng {readable_name}"