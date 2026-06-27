from typing import List, Optional
import numpy as np


class EmbeddingGenerator:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "default"
        self._init_embedding_function()

    def _init_embedding_function(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.use_sentence_transformers = True
        except ImportError:
            print("警告: sentence-transformers未安装,使用简单哈希嵌入")
            self.use_sentence_transformers = False

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.use_sentence_transformers:
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        else:
            return self._simple_hash_embeddings(texts)

    def generate_embedding(self, text: str) -> List[float]:
        return self.generate_embeddings([text])[0]

    def _simple_hash_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        embedding_dim = 384
        for text in texts:
            hash_value = hash(text)
            rng = np.random.RandomState(hash_value & 0xffffffff)
            embedding = rng.rand(embedding_dim)
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())
        return embeddings

    def get_embedding_dim(self) -> int:
        if self.use_sentence_transformers:
            return self.model.get_sentence_embedding_dimension()
        return 384
