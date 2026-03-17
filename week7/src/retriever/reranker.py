from sentence_transformers import CrossEncoder

# Cross-encoder scores for ms-marco-MiniLM-L-6-v2 are unbounded.
# Empirically: > 0 = likely relevant, < 0 = likely noise/off-topic.
# A threshold of 0.0 filters clear negatives while keeping weak-but-real matches.
# Raise to e.g. 1.0 if you want stricter relevance.
MIN_RELEVANCE_SCORE = 0.0


class Reranker:
    def __init__(self, top_n=3, min_score: float = MIN_RELEVANCE_SCORE):
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.top_n = top_n
        self.min_score = min_score

    def rerank(self, query, documents):
        
        if not documents:
            return [], float("-inf")

        print(f"Reranking {len(documents)} candidates using Cross-Encoder...")

        pairs = [(query, doc.page_content) for doc in documents]
        scores = self.model.predict(pairs)

        # Sort descending
        scored = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)

        all_scores = [round(float(s), 4) for s, _ in scored]
        print(f"   All scores: {all_scores}")

        # Filter below threshold
        passing = [(s, doc) for s, doc in scored if float(s) >= self.min_score]
        filtered_count = len(scored) - len(passing)
        if filtered_count:
            print(f"   Filtered out {filtered_count} chunk(s) below threshold ({self.min_score})")

        if not passing:
            print(f"   No chunks passed the relevance threshold — context will be empty.")
            return [], float("-inf")

        top_docs = [doc for _, doc in passing[:self.top_n]]
        top_score = float(passing[0][0])
        print(f"   Kept {len(top_docs)} chunk(s). Best score: {round(top_score, 4)}")
        return top_docs, top_score