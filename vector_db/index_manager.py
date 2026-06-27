import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from vector_db.chroma_client import ChromaDBClient


class IndexManager:
    def __init__(self, chroma_client: ChromaDBClient):
        self.client = chroma_client
        self.index_metadata_file = "./chroma_db/index_metadata.json"
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        if not os.path.exists(os.path.dirname(self.index_metadata_file)):
            os.makedirs(os.path.dirname(self.index_metadata_file), exist_ok=True)
        if not os.path.exists(self.index_metadata_file):
            self._save_metadata({})

    def _load_metadata(self) -> Dict[str, Any]:
        if os.path.exists(self.index_metadata_file):
            with open(self.index_metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_metadata(self, metadata: Dict[str, Any]):
        with open(self.index_metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def add_knowledge_documents(
        self,
        documents: List[str],
        doc_type: str = "knowledge",
        source: Optional[str] = None
    ) -> List[str]:
        metadatas = []
        for doc in documents:
            metadata = {
                "type": doc_type,
                "source": source or "manual",
                "created_at": datetime.now().isoformat()
            }
            metadatas.append(metadata)
        return self.client.add_documents(
            documents=documents,
            metadatas=metadatas
        )

    def add_risk_assessment_cases(
        self,
        cases: List[Dict[str, Any]]
    ) -> List[str]:
        documents = []
        metadatas = []
        for case in cases:
            doc = f"区域: {case.get('region', '')}\n"
            doc += f"风险等级: {case.get('risk_level', '')}\n"
            doc += f"评估说明: {case.get('explanation', '')}\n"
            doc += f"关键因素: {', '.join(case.get('key_factors', []))}"
            documents.append(doc)
            metadatas.append({
                "type": "risk_case",
                "region": case.get('region', ''),
                "risk_level": case.get('risk_level', ''),
                "created_at": datetime.now().isoformat()
            })
        return self.client.add_documents(
            documents=documents,
            metadatas=metadatas
        )

    def get_index_stats(self) -> Dict[str, Any]:
        total_count = self.client.count()
        metadata = self._load_metadata()
        type_counts = {}
        all_docs = self.client.get()
        for meta in all_docs.get('metadatas', []):
            doc_type = meta.get('type', 'unknown')
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return {
            "total_documents": total_count,
            "documents_by_type": type_counts,
            "last_updated": metadata.get('last_updated'),
            "collections": self.client.list_collections()
        }

    def backup_index(self, backup_name: Optional[str] = None) -> str:
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        metadata = self._load_metadata()
        metadata['last_backup'] = datetime.now().isoformat()
        metadata['last_backup_name'] = backup_name
        self._save_metadata(metadata)
        return backup_name

    def get_document_types(self) -> List[str]:
        all_docs = self.client.get()
        types = set()
        for meta in all_docs.get('metadatas', []):
            types.add(meta.get('type', 'unknown'))
        return sorted(list(types))

    def clear_index(self):
        self.client.reset_collection()
        self._save_metadata({
            "last_cleared": datetime.now().isoformat()
        })
