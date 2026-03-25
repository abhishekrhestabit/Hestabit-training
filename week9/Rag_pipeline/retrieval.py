from qdrant_client import QdrantClient, models
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding

class Vectorizer:
    def __init__(self, dense_model="sentence-transformers/all-MiniLM-L6-v2", sparse_model="prithivida/Splade_PP_en_v1"):
        self.dense_model = SentenceTransformer(dense_model)
        self.sparse_model = SparseTextEmbedding(model_name=sparse_model)

    def encode(self, texts: List[str]):
        dense_vectors = self.dense_model.encode(texts).tolist()
        sparse_vectors = list(self.sparse_model.embed(texts))
        return dense_vectors, sparse_vectors

class Retriever:
    def __init__(self, collection_name="rag_store"):
        self.client = QdrantClient(path="./qdrant_db")
        self.collection = collection_name
        self.vectorizer = Vectorizer()

    def hybrid_search(self, query: str, limit: int = 5):
        dense, sparse = self.vectorizer.encode([query])
        
        search_result = self.client.search(
            collection_name=self.collection,
            query_vector=models.NamedVector(
                name="dense",
                vector=dense[0]
            ),
            query_sparse_vector=models.NamedSparseVector(
                name="sparse",
                vector=models.SparseVector(
                    indices=sparse[0].indices.tolist(),
                    values=sparse[0].values.tolist()
                )
            ),
            limit=limit,
            with_payload=True
        )
        return [hit.payload for hit in search_result]

    def create_points(self, chunks: List[str], metadatas: List[Dict[str, Any]], start_id: int):
        dense, sparse = self.vectorizer.encode(chunks)
        points = []
        for i in range(len(chunks)):
            points.append(
                models.PointStruct(
                    id=start_id + i,
                    vector={
                        "dense": dense[i],
                        "sparse": models.SparseVector(
                            indices=sparse[i].indices.tolist(),
                            values=sparse[i].values.tolist()
                        )
                    },
                    payload={**metadatas[i], "text": chunks[i]}
                )
            )
        return points

    def batch_upsert(self, chunks: List[str], metadatas: List[Dict[str, Any]], batch_size: int = 200):
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            points = self.create_points(batch_chunks, batch_meta, i)
            
            self.client.upsert(
                collection_name=self.collection,
                points=points
            )