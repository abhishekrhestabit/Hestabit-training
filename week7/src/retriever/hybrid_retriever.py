import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from src.embeddings.embedder import Embedder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vectorstore", "db_faiss")

class HybridRetriever:
    def __init__(self, top_k=5):
        self.top_k = top_k
        self.embeddings = Embedder().get_embeddings()
        self.faiss_db = self._load_faiss_db()
        self.bm25_retriever = self._build_bm25()
        self.semantic_retriever = self.faiss_db.as_retriever(
            search_type="mmr",
            search_kwargs={"k": top_k, "fetch_k": 20}
        )

    def _load_faiss_db(self):
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"FAISS DB not found at {DB_PATH}. Run ingest.py first.")
        return FAISS.load_local(DB_PATH, self.embeddings, allow_dangerous_deserialization=True)

    def _build_bm25(self):
        docs = list(self.faiss_db.docstore._dict.values())
        if not docs:
            raise ValueError("No documents found in FAISS docstore.")
        retriever = BM25Retriever.from_documents(docs)
        retriever.k = self.top_k
        return retriever

    def _rrf(self, *ranked_lists, k=60):
        """Reciprocal Rank Fusion over multiple ranked doc lists."""
        scores = {}
        all_docs = {}
        for ranked in ranked_lists:
            for rank, doc in enumerate(ranked):
                key = doc.page_content
                scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
                all_docs[key] = doc
        sorted_keys = sorted(scores, key=scores.__getitem__, reverse=True)
        return [all_docs[k] for k in sorted_keys]

    def retrieve(self, query, filters=None):
        print(f"Executing Hybrid Search for: '{query}'")
        semantic_docs = self.semantic_retriever.invoke(query)
        bm25_docs = self.bm25_retriever.invoke(query)
        fused = self._rrf(semantic_docs, bm25_docs)
        if filters:
            fused = [d for d in fused if all(d.metadata.get(k) == v for k, v in filters.items())]
        return fused[:self.top_k]