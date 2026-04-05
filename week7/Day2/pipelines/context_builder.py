import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.retriever.hybrid_retriever import HybridRetriever
from src.retriever.reranker import Reranker


class ContextBuilder:
    def __init__(self):
        self.retriever = HybridRetriever(top_k=10)
        self.reranker = Reranker(top_n=5)

    def _deduplicate(self, documents):
        seen, unique = set(), []
        for doc in documents:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                unique.append(doc)
        print(f"Deduplication: {len(documents)} -> {len(unique)} chunks.")
        return unique

    def build_context(self, query, filters=None):
       
        # 1. Hybrid Retrieval (Vector MMR + BM25)
        raw_docs = self.retriever.retrieve(query, filters=filters)

        # 2. Deduplicate
        unique_docs = self._deduplicate(raw_docs)

        # 3. Rerank + threshold filter
        final_docs, top_score = self.reranker.rerank(query, unique_docs)

        # 4. Format with traceability
        context_string = ""
        for i, doc in enumerate(final_docs):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            context_string += f"\n[Document {i+1}]\n"
            context_string += f"Source: {source} (Page {page})\n"
            context_string += f"Content: {doc.page_content}\n"
            context_string += "-" * 40

        return context_string, final_docs, top_score


if __name__ == "__main__":
    query = "Explain how credit underwriting works"
    filters = {"file_type": "pdf", "tag": "document"}

    builder = ContextBuilder()
    formatted_context, docs, top_score = builder.build_context(query, filters=filters)

    print("\nFinal Traceable Context:\n")
    print(formatted_context)
    print(f"\n{len(docs)} chunks passed to context window. Best score: {round(top_score, 4)}")