import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.retriever.hybrid_retriever import HybridRetriever
from src.retriever.reranker import Reranker

class ContextBuilder:
    def __init__(self):
        self.retriever = HybridRetriever(top_k=10) # Fetch wide net first
        self.reranker = Reranker(top_n=5)          # Narrow down to best 5

    def _deduplicate(self, documents):
        """Removes exact duplicate chunks based on page_content."""
        seen_content = set()
        unique_docs = []
        for doc in documents:
            if doc.page_content not in seen_content:
                seen_content.add(doc.page_content)
                unique_docs.append(doc)
        print(f"Deduplication: {len(documents)} -> {len(unique_docs)} chunks.")
        return unique_docs

    def build_context(self, query, filters=None):
        # 1. Hybrid Retrieval (Vector MMR + BM25) 
        raw_docs = self.retriever.retrieve(query, filters=filters)
        
        # 2. Deduplicate
        unique_docs = self._deduplicate(raw_docs)
        
        # 3. Rerank (Cross-Encoder)
        final_docs = self.reranker.rerank(query, unique_docs)

        # 4. Format Output with Traceability
        context_string = ""
        for i, doc in enumerate(final_docs):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            
            context_string += f"\n[Document {i+1}]\n"
            context_string += f"Source: {source} (Page {page})\n"
            context_string += f"Content: {doc.page_content}\n"
            context_string += "-" * 40

        return context_string, final_docs

if __name__ == "__main__":
    # Exercise: hardcoded query as specified in Day 2
    query = "Explain how credit underwriting works"
    top_k = 5
    filters = {"file_type": "pdf", "tag": "document"}

    builder = ContextBuilder()
    formatted_context, docs = builder.build_context(query, filters=filters)

    print("\nFinal Traceable Context:\n")
    print(formatted_context)
    print(f"\n{len(docs)} chunks passed to context window.")