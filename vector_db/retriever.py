import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Dict, Any, Optional
from vector_db.chroma_client import ChromaDBClient


class VectorRetriever:
    def __init__(self, chroma_client: ChromaDBClient):
        self.client = chroma_client

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        results = self.client.query(
            query_texts=[query],
            n_results=n_results,
            where=filters
        )
        return self._format_results(results)

    def search_by_metadata(
        self,
        metadata_filters: Dict[str, Any],
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        results = self.client.get(
            where=metadata_filters
        )
        return self._format_get_results(results)

    def hybrid_search(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        results = self.client.query(
            query_texts=[query],
            n_results=n_results,
            where=metadata_filters
        )
        return self._format_results(results)

    def get_relevant_context(
        self,
        query: str,
        context_type: Optional[str] = None,
        n_results: int = 3
    ) -> str:
        filters = {"type": context_type} if context_type else None
        results = self.search(query, n_results=n_results, filters=filters)
        context_parts = []
        for idx, result in enumerate(results, 1):
            context_parts.append(f"[相关信息 {idx}]\n{result['document']}")
        return "\n\n".join(context_parts)

    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        formatted = []
        if not results.get('documents'):
            return formatted
        for i in range(len(results['documents'][0])):
            formatted.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                'distance': results['distances'][0][i] if results['distances'] else None
            })
        return formatted

    def _format_get_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        formatted = []
        if not results.get('documents'):
            return formatted
        for i in range(len(results['documents'])):
            formatted.append({
                'id': results['ids'][i],
                'document': results['documents'][i],
                'metadata': results['metadatas'][i] if results['metadatas'] else {}
            })
        return formatted
