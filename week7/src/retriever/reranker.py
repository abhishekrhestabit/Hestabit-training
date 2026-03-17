from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, top_n=3):
        # ms-marco is the industry standard cross-encoder for passage reranking
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.top_n = top_n

    def rerank(self, query, documents):
        """
        Takes a list of candidate documents and re-scores them against the query
        using a cross-encoder. Returns top_n documents sorted by relevance score.
        """
        if not documents:
            return []

        print(f"Reranking {len(documents)} candidates using Cross-Encoder...")

        # Score every (query, chunk) pair
        pairs = [(query, doc.page_content) for doc in documents]
        scores = self.model.predict(pairs)

        # Sort by score descending, take top_n
        scored = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        top_docs = [doc for _, doc in scored[:self.top_n]]

        print(f"   Top scores: {[round(float(s), 4) for s, _ in scored[:self.top_n]]}")
        return top_docs