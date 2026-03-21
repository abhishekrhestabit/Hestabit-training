"""
memory/vector_store.py
─────────────────────────────────────────────────────────────────
Vector memory using FAISS + sentence-transformers.

Stores text as dense embeddings and retrieves the most similar
entries given a query — enabling semantic (meaning-based) recall
rather than exact keyword matching.

Used by Day 4 pipeline to:
    • Store important facts / task results after each query
    • Retrieve relevant past context before answering a new query
    • Inject that context into the LLM prompt

Design:
    • Embeddings: sentence-transformers "all-MiniLM-L6-v2"
      (384-dim, fast on CPU, ~80MB download once)
    • Index: FAISS IndexFlatL2 (exact nearest-neighbour, CPU-safe)
    • Persistence: index saved to disk as .faiss + .json metadata
─────────────────────────────────────────────────────────────────
"""

import json
import os
import time
import subprocess
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────
#  Lazy imports — install if missing
# ─────────────────────────────────────────────────────────────────

def _ensure_packages():
    """Install faiss-cpu and sentence-transformers if not present."""
    packages = {
        "faiss":               "faiss-cpu",
        "sentence_transformers": "sentence-transformers",
    }
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"[VectorStore] Installing {pip_name}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name, "-q"],
                check=True,
            )
            print(f"[VectorStore] ✅ {pip_name} installed.")


# ─────────────────────────────────────────────────────────────────
#  VectorStore
# ─────────────────────────────────────────────────────────────────

class VectorStore:
    """
    FAISS-backed semantic memory.

    Args:
        store_path: Directory where index files are saved.
        model_name: SentenceTransformer model to use for embeddings.
        top_k:      How many results to return on search.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"   # 384-dim, fast, good quality
    INDEX_FILE = "memory.faiss"
    META_FILE  = "memory.json"

    def __init__(
        self,
        store_path: str = "memory",
        top_k: int      = 3,
    ):
        _ensure_packages()

        import faiss
        from sentence_transformers import SentenceTransformer

        self._faiss  = faiss
        self._top_k  = top_k
        self._path   = Path(store_path)
        self._path.mkdir(parents=True, exist_ok=True)

        print(f"[VectorStore] Loading embedding model: {self.MODEL_NAME} ...")
        self._model = SentenceTransformer(self.MODEL_NAME)
        self._dim   = self._model.get_sentence_embedding_dimension()

        # Load existing index or create fresh
        index_path = self._path / self.INDEX_FILE
        meta_path  = self._path / self.META_FILE

        if index_path.exists() and meta_path.exists():
            self._index = faiss.read_index(str(index_path))
            with open(meta_path, "r", encoding="utf-8") as f:
                self._metadata: list[dict] = json.load(f)
            print(f"[VectorStore] Loaded {len(self._metadata)} stored memories.")
        else:
            self._index    = faiss.IndexFlatL2(self._dim)
            self._metadata = []
            print("[VectorStore] Fresh index created.")

    # ── Write ─────────────────────────────────────────────────────

    def add(self, text: str, metadata: dict | None = None) -> None:
        """
        Embed `text` and store it in the index.

        Args:
            text:     The text to store (query, answer, fact, etc.)
            metadata: Optional dict with extra info (source, timestamp, tags).
        """
        import numpy as np

        embedding = self._model.encode([text], convert_to_numpy=True)
        self._index.add(embedding.astype("float32"))

        entry = {
            "text":      text,
            "timestamp": time.time(),
            **(metadata or {}),
        }
        self._metadata.append(entry)
        self._save()

    def add_many(self, texts: list[str], metadata_list: list[dict] | None = None) -> None:
        """Add multiple texts in one batch (faster than calling add() in a loop)."""
        import numpy as np

        if not texts:
            return

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        self._index.add(embeddings.astype("float32"))

        for i, text in enumerate(texts):
            meta = (metadata_list[i] if metadata_list and i < len(metadata_list) else {})
            self._metadata.append({
                "text":      text,
                "timestamp": time.time(),
                **meta,
            })
        self._save()

    # ── Search ────────────────────────────────────────────────────

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Find the most semantically similar stored entries.

        Returns a list of dicts:
            [{"text": "...", "score": 0.12, "timestamp": ..., ...}, ...]
        Score = L2 distance (lower = more similar).
        """
        k = min(top_k or self._top_k, self._index.ntotal)
        if k == 0:
            return []

        embedding = self._model.encode([query], convert_to_numpy=True)
        distances, indices = self._index.search(embedding.astype("float32"), k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            entry = dict(self._metadata[idx])
            entry["score"] = float(dist)
            results.append(entry)

        return results

    def search_as_context(self, query: str, top_k: int | None = None) -> str:
        """
        Search and return results as a plain string ready to inject into a prompt.
        Returns empty string if no memories exist yet.
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return ""
        lines = ["── Relevant past memories ──"]
        for i, r in enumerate(results, 1):
            lines.append(f"  [{i}] {r['text']}")
        return "\n".join(lines)

    def recall_context(self, query: str) -> str:
        """
        Semantic recall for a query — returns context string for prompt injection.
        Called by the pipeline's recall step before planning.
        """
        return self.search_as_context(query)

    def store_episode(self, query: str, answer: str) -> None:
        """
        Embed and store a completed query+answer pair.
        Called by the pipeline after every successful run.
        """
        summary = answer[:300] + ("..." if len(answer) > 300 else "")
        self.add(f"Q: {query}", metadata={"type": "query"})
        self.add(f"A: {summary}", metadata={"type": "answer"})

    def store_fact(self, fact: str) -> None:
        """
        Embed and store a single semantic fact.
        Called after fact extraction from Q&A pairs.
        """
        self.add(fact, metadata={"type": "fact"})

    # ── Inspect ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return self._index.ntotal

    def clear(self) -> None:
        """Wipe all stored memories."""
        import faiss
        self._index    = faiss.IndexFlatL2(self._dim)
        self._metadata = []
        self._save()
        print("[VectorStore] Cleared all memories.")

    def display(self, n: int = 10) -> None:
        """Print the most recently stored memories."""
        print(f"\n── Vector Store ({self.count} memories) ──")
        for i, m in enumerate(self._metadata[-n:], 1):
            print(f"  [{i}] {m['text'][:120]}")
        print()

    # ── Persistence ───────────────────────────────────────────────

    def _save(self) -> None:
        """Persist index and metadata to disk."""
        self._faiss.write_index(self._index, str(self._path / self.INDEX_FILE))
        with open(self._path / self.META_FILE, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2)