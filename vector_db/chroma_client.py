import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from collections import defaultdict


class SimpleVectorDB:
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "low_altitude_risk"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self._index: Dict[str, List[int]] = defaultdict(list)
        self._initialize()

    def _initialize(self):
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory, exist_ok=True)
        self._load_from_disk()

    def _save_to_disk(self):
        data_file = os.path.join(self.persist_directory, f"{self.collection_name}.json")
        data = {
            "documents": self.documents,
            "metadatas": self.metadatas,
            "ids": self.ids
        }
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_from_disk(self):
        data_file = os.path.join(self.persist_directory, f"{self.collection_name}.json")
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.documents = data.get("documents", [])
                self.metadatas = data.get("metadatas", [])
                self.ids = data.get("ids", [])
                self._rebuild_index()
            except Exception as e:
                print(f"加载数据库失败: {e}")

    def _rebuild_index(self):
        self._index.clear()
        for idx, doc in enumerate(self.documents):
            words = self._tokenize(doc)
            for word in words:
                self._index[word].append(idx)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        words = []
        current = []
        for char in text:
            if char.isalnum() or char in [',', '。', ',', ';', ':', '!', '?']:
                current.append(char)
            else:
                if current:
                    words.append(''.join(current))
                    current = []
        if current:
            words.append(''.join(current))
        return words

    def _compute_similarity(self, query: str, doc: str) -> float:
        query_words = set(self._tokenize(query))
        doc_words = set(self._tokenize(doc))
        if not query_words:
            return 0.0
        intersection = query_words & doc_words
        union = query_words | doc_words
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        if ids is None:
            ids = [f"doc_{hashlib.md5(doc.encode()).hexdigest()[:8]}_{i}"
                   for i, doc in enumerate(documents, len(self.documents))]
        if metadatas is None:
            metadatas = [{} for _ in range(len(documents))]
        for i, doc in enumerate(documents):
            self.documents.append(doc)
            self.metadatas.append(metadatas[i])
            self.ids.append(ids[i])
            words = self._tokenize(doc)
            idx = len(self.documents) - 1
            for word in words:
                self._index[word].append(idx)
        self._save_to_disk()
        return ids

    def query(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        results = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        for query in query_texts:
            scores = []
            for idx, doc in enumerate(self.documents):
                if where:
                    match = True
                    for key, value in where.items():
                        if self.metadatas[idx].get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                if where_document:
                    if "$contains" in where_document:
                        if where_document["$contains"] not in doc:
                            continue
                score = self._compute_similarity(query, doc)
                scores.append((-score, idx))
            scores.sort()
            top_indices = [idx for (neg_score, idx) in scores[:n_results]]
            results["ids"].append([self.ids[idx] for idx in top_indices])
            results["documents"].append([self.documents[idx] for idx in top_indices])
            results["metadatas"].append([self.metadatas[idx] for idx in top_indices])
            results["distances"].append([-neg_score for (neg_score, idx) in scores[:n_results]])
        return results

    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        result_ids = []
        result_docs = []
        result_metas = []
        for idx, doc_id in enumerate(self.ids):
            if ids is not None and doc_id not in ids:
                continue
            if where:
                match = True
                for key, value in where.items():
                    if self.metadatas[idx].get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            result_ids.append(doc_id)
            result_docs.append(self.documents[idx])
            result_metas.append(self.metadatas[idx])
        return {
            "ids": result_ids,
            "documents": result_docs,
            "metadatas": result_metas
        }

    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        for i, doc_id in enumerate(ids):
            try:
                idx = self.ids.index(doc_id)
                if documents and i < len(documents):
                    self.documents[idx] = documents[i]
                if metadatas and i < len(metadatas):
                    self.metadatas[idx] = metadatas[i]
            except ValueError:
                continue
        self._rebuild_index()
        self._save_to_disk()

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ):
        to_delete = set()
        if ids is not None:
            to_delete.update(ids)
        if where:
            for idx, doc_id in enumerate(self.ids):
                match = True
                for key, value in where.items():
                    if self.metadatas[idx].get(key) != value:
                        match = False
                        break
                if match:
                    to_delete.add(doc_id)
        new_docs = []
        new_metas = []
        new_ids = []
        for idx, doc_id in enumerate(self.ids):
            if doc_id not in to_delete:
                new_docs.append(self.documents[idx])
                new_metas.append(self.metadatas[idx])
                new_ids.append(doc_id)
        self.documents = new_docs
        self.metadatas = new_metas
        self.ids = new_ids
        self._rebuild_index()
        self._save_to_disk()

    def count(self) -> int:
        return len(self.documents)

    def reset_collection(self):
        self.documents = []
        self.metadatas = []
        self.ids = []
        self._index.clear()
        self._save_to_disk()

    def list_collections(self) -> List[str]:
        if not os.path.exists(self.persist_directory):
            return []
        collections = []
        for filename in os.listdir(self.persist_directory):
            if filename.endswith('.json'):
                collections.append(filename[:-5])
        return collections


ChromaDBClient = SimpleVectorDB
