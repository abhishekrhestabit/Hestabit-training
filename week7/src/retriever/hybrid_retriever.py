import os
import sys
from collections import defaultdict

# Add week7/ to path
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

    def _load_faiss_db(self):
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"❌ FAISS DB not found at {DB_PATH}. Run ingest.py first.")
        return FAISS.load_local(DB_PATH, self.embeddings, allow_dangerous_deserialization=True)

    def _build_bm25(self):
        # Extract all documents from FAISS docstore to build the BM25 index
        docs = list(self.faiss_db.docstore._dict.values())
        if not docs:
            raise ValueError("No documents found in FAISS docstore.")
        retriever = BM25Retriever.from_documents(docs)
        retriever.k = self.top_k
        return retriever

    def _reciprocal_rank_fusion(self, semantic_docs, keyword_docs, k=60):
        """
        Merges two ranked lists using Reciprocal Rank Fusion (RRF).
        RRF score = sum of 1 / (k + rank) across all lists.
        Higher score = more relevant.
        """
        scores = defaultdict(float)
        doc_map = {}

        for rank, doc in enumerate(semantic_docs):
            key = doc.page_content
            scores[key] += 1 / (k + rank + 1)
            doc_map[key] = doc

        for rank, doc in enumerate(keyword_docs):
            key = doc.page_content
            scores[key] += 1 / (k + rank + 1)
            doc_map[key] = doc

        # Sort by fused score descending
        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys]

    def retrieve(self, query, filters=None):
        """
        Retrieves documents using hybrid search (MMR semantic + BM25 keyword),
        fused with Reciprocal Rank Fusion. Optionally filters by metadata.
        """
        print(f"🔎 Executing Hybrid Search for: '{query}'")

        # 1. Semantic search with MMR for diversity
        semantic_docs = self.faiss_db.max_marginal_relevance_search(
            query, k=self.top_k, fetch_k=20
        )

        # 2. BM25 keyword search
        keyword_docs = self.bm25_retriever.invoke(query)

        # 3. Fuse results with RRF
        fused_docs = self._reciprocal_rank_fusion(semantic_docs, keyword_docs)

        # 4. Apply metadata filters if provided (e.g., {"year": "2024", "type": "policy"})
        if filters:
            fused_docs = [
                doc for doc in fused_docs
                if all(doc.metadata.get(k) == v for k, v in filters.items())
            ]

        return fused_docs[:self.top_k]

if __name__ == "__main__":
    # Exercise: hardcoded query as specified in Day 2
    query = "Explain how credit underwriting works"
    top_k = 5
    filters = {"file_type": "pdf", "tag": "document"}

    hr = HybridRetriever(top_k=top_k)
    results = hr.retrieve(query, filters=filters)

    print()
    for i, doc in enumerate(results, 1):
        print(f"── Result {i} ──────────────────────────────")
        print(f"📄 Source : {doc.metadata.get('source', 'unknown')}")
        print(f"📃 Page   : {doc.metadata.get('page', 'N/A')}")
        print(f"📝 Content:\n{doc.page_content[:400]}")
        print()