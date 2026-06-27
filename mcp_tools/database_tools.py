import sqlite3
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
class DatabaseTool:
    def __init__(self, db_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, 'risk_assessment.db')
        self.db_path = db_path
        self._init_database()
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS assessment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                assessment_data TEXT,
                model_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                content TEXT,
                source TEXT,
                is_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_path TEXT,
                accuracy REAL,
                training_samples INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                endpoint TEXT,
                request_data TEXT,
                response_data TEXT,
                status_code INTEGER,
                response_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
    def query_data(self, table: str, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        valid_tables = ['assessment_history', 'training_data', 'models', 'api_logs']
        with self._get_connection() as conn:
            query = f'SELECT * FROM {table}'
            params = []
            conditions = []
            if filters:
                for key, value in filters.items():
                    conditions.append(f'{key} = ?')
                    params.append(value)
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            query += ' ORDER BY created_at DESC'
            if limit:
                query += f' LIMIT {limit}'
            query += f' OFFSET {offset}'
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                for field in result:
                    if isinstance(result[field], str):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, ValueError):
                            pass
                results.append(result)
            return results
    def insert_data(self, table: str, data: Dict[str, Any]) -> int:
        valid_tables = ['assessment_history', 'training_data', 'models', 'api_logs']
        with self._get_connection() as conn:
            data_to_insert = data.copy()
            for field in data_to_insert:
                if isinstance(data_to_insert[field], (dict, list)):
                    data_to_insert[field] = json.dumps(data_to_insert[field], ensure_ascii=False)
            columns = list(data_to_insert.keys())
            placeholders = ['?' for _ in columns]
            values = list(data_to_insert.values())
            query = f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({", ".join(placeholders)})'
            cursor = conn.cursor()
            cursor.execute(query, values)
            return cursor.lastrowid
    def update_data(self, table: str, data_id: int, updates: Dict[str, Any]) -> bool:
        valid_tables = ['assessment_history', 'training_data', 'models', 'api_logs']
        with self._get_connection() as conn:
            updates_to_apply = updates.copy()
            for field in updates_to_apply:
                if isinstance(updates_to_apply[field], (dict, list)):
                    updates_to_apply[field] = json.dumps(updates_to_apply[field], ensure_ascii=False)
            set_clause = ', '.join([f'{key} = ?' for key in updates_to_apply.keys()])
            values = list(updates_to_apply.values()) + [data_id]
            query = f'UPDATE {table} SET {set_clause} WHERE id = ?'
            cursor = conn.cursor()
            cursor.execute(query, values)
            return cursor.rowcount > 0
    def delete_data(self, table: str, data_id: int) -> bool:
        valid_tables = ['assessment_history', 'training_data', 'models', 'api_logs']
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {table} WHERE id = ?', (data_id,))
            return cursor.rowcount > 0
    def save_assessment(self, region: str, risk_level: str, assessment_data: Dict[str, Any], model_used: str = 'base_model') -> int:
        data = {'region': region, 'risk_level': risk_level, 'assessment_data': assessment_data, 'model_used': model_used}
        return self.insert_data('assessment_history', data)
    def get_assessment_history(self, region: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        filters = {}
        if region:
            filters['region'] = region
        return self.query_data('assessment_history', filters, limit=limit)
    def save_training_data(self, data_type: str, content: Any, source: Optional[str] = None) -> int:
        data = {'data_type': data_type, 'content': content, 'source': source}
        return self.insert_data('training_data', data)
    def get_training_data(self, data_type: Optional[str] = None, unused_only: bool = False, limit: int = 1000) -> List[Dict[str, Any]]:
        filters = {}
        if data_type:
            filters['data_type'] = data_type
        if unused_only:
            filters['is_used'] = 0
        return self.query_data('training_data', filters, limit=limit)
    def mark_training_data_used(self, data_ids: List[int]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for data_id in data_ids:
                cursor.execute('UPDATE training_data SET is_used = 1 WHERE id = ?', (data_id,))
    def save_model(self, model_name: str, model_path: str, accuracy: Optional[float] = None, training_samples: Optional[int] = None, description: Optional[str] = None) -> int:
        data = {'model_name': model_name, 'model_path': model_path, 'accuracy': accuracy, 'training_samples': training_samples, 'description': description}
        return self.insert_data('models', data)
    def get_models(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.query_data('models', limit=limit)
    def log_api_call(self, api_name: str, endpoint: Optional[str] = None, request_data: Optional[Any] = None, response_data: Optional[Any] = None, status_code: Optional[int] = None, response_time: Optional[float] = None) -> int:
        data = {'api_name': api_name, 'endpoint': endpoint, 'request_data': request_data, 'response_data': response_data, 'status_code': status_code, 'response_time': response_time}
        return self.insert_data('api_logs', data)
    def get_statistics(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            stats = {}
            cursor.execute('SELECT COUNT(*) FROM assessment_history')
            stats['total_assessments'] = cursor.fetchone()[0]
            cursor.execute('SELECT risk_level, COUNT(*) FROM assessment_history GROUP BY risk_level')
            stats['risk_level_distribution'] = dict(cursor.fetchall())
            cursor.execute('SELECT COUNT(*) FROM training_data')
            stats['total_training_data'] = cursor.fetchone()[0]
            cursor.execute('SELECT data_type, COUNT(*) FROM training_data GROUP BY data_type')
            stats['training_data_by_type'] = dict(cursor.fetchall())
            cursor.execute('SELECT COUNT(*) FROM models')
            stats['total_models'] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM api_logs')
            stats['total_api_calls'] = cursor.fetchone()[0]
            cursor.execute('SELECT api_name, COUNT(*) FROM api_logs GROUP BY api_name')
            stats['api_calls_by_name'] = dict(cursor.fetchall())
            return stats
_db_tool_instance: Optional[DatabaseTool] = None
def get_database_tool(db_path: Optional[str] = None) -> DatabaseTool:
    global _db_tool_instance
    if _db_tool_instance is None:
        _db_tool_instance = DatabaseTool(db_path)
    return _db_tool_instance
