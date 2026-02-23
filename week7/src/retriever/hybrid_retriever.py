import os
import sys

# Add week7/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.retrievers import EnsembleRetriever
from src.embeddings.embedder import Embedder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vectorstore", "db_faiss")

class HybridRetriever:
    def __init__(self, top_k=5):
        self.top_k = top_k
        self.embeddings = Embedder().get_embeddings()
        
        # Load the base engines
        self.faiss_db = self._load_faiss_db()
        self.bm25_retriever = self._build_bm25()
        
        # Initialize the official LangChain RRF wrapper
        self.ensemble = self._build_ensemble()

    def _load_faiss_db(self):
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"❌ FAISS DB not found at {DB_PATH}. Run ingest.py first.")
        return FAISS.load_local(DB_PATH, self.embeddings, allow_dangerous_deserialization=True)

    def _build_bm25(self):
        docs = list(self.faiss_db.docstore._dict.values())
        if not docs:
            raise ValueError("No documents found in FAISS docstore.")
        retriever = BM25Retriever.from_documents(docs)
        retriever.k = self.top_k
        return retriever

    def _build_ensemble(self):
        """Wraps FAISS and BM25 into a single object that handles RRF automatically."""
        # Setup Semantic Retriever (with MMR)
        semantic_retriever = self.faiss_db.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": self.top_k, "fetch_k": 20}
        )
        
        # Combine them using EnsembleRetriever
        # The 'weights' parameter automatically handles the Reciprocal Rank Fusion math
        return EnsembleRetriever(
            retrievers=[semantic_retriever, self.bm25_retriever],
            weights=[0.5, 0.5] # 50% Semantic, 50% Keyword
        )

    def retrieve(self, query, filters=None):
        """
        Retrieves documents using the built-in EnsembleRetriever.
        """
        print(f"🔎 Executing Hybrid Search for: '{query}'")

        # The library executes both engines in parallel and applies RRF for you
        fused_docs = self.ensemble.invoke(query)

        # Apply metadata filters post-retrieval
        if filters:
            fused_docs = [
                doc for doc in fused_docs
                if all(doc.metadata.get(k) == v for k, v in filters.items())
            ]

        return fused_docs[:self.top_k]