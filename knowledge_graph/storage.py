import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from typing import Optional
from knowledge_graph.schema import KnowledgeGraph

class KnowledgeGraphStorage:
    def __init__(self, storage_path: str = './knowledge_graph/data'):
        self.storage_path = storage_path
    
    def _ensure_storage_path(self):
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_file_path(self, name: str) -> str:
        return os.path.join(self.storage_path, f'{name}.json')
    
    def save(self, kg: KnowledgeGraph, name: str = 'knowledge_graph') -> str:
        self._ensure_storage_path()
        file_path = self._get_file_path(name)
        data = kg.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return file_path
    
    def load(self, name: str = 'knowledge_graph') -> Optional[KnowledgeGraph]:
        file_path = self._get_file_path(name)
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return KnowledgeGraph.from_dict(data)
    
    def exists(self, name: str = 'knowledge_graph') -> bool:
        file_path = self._get_file_path(name)
        return os.path.exists(file_path)
    
    def delete(self, name: str = 'knowledge_graph') -> bool:
        file_path = self._get_file_path(name)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    def list_available(self) -> list:
        if not os.path.exists(self.storage_path):
            return []
        files = os.listdir(self.storage_path)
        return [f[:-5] for f in files if f.endswith('.json')]
