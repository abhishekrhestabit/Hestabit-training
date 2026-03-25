import os
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

class Vectorizer:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]):
        # Generates dense vectors
        return self.model.encode(texts)

class VectorStore:
    def __init__(self, collection_name: str = "rag_store"):
        self.client = QdrantClient(path="./qdrant_db")
        self.collection = collection_name
        self.vectorizer = Vectorizer()
        self._ensure_collection()

    def _ensure_collection(self):
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    "dense": models.VectorParams(size=384, distance=models.Distance.COSINE)
                }
            )

    def _prepare_points(self, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]]) -> List[models.PointStruct]:
        embeddings = self.vectorizer.encode(texts)
        points = []
        for i, (idx, meta) in enumerate(zip(ids, metadatas)):
            points.append(
                models.PointStruct(
                    id=idx,
                    vector={"dense": embeddings[i].tolist()},
                    payload=meta
                )
            )
        return points

    def upsert_batch(self, documents: List[str], ids: List[str], metadatas: List[Dict[str, Any]], batch_size: int = 200):
        """
        Upserts documents in batches to ensure memory efficiency and prevent timeouts.
        """
        for i in range(0, len(documents), batch_size):
            batch_texts = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]

            points = self._prepare_points(batch_ids, batch_texts, batch_metas)
            self.client.upsert(
                collection_name=self.collection,
                points=points
            )