from __future__ import annotations
import json, pickle, sqlite3
from pathlib import Path
from datetime import datetime, timezone

import numpy as np


def _deps():
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
        return faiss, SentenceTransformer
    except ImportError:
        raise ImportError("pip install faiss-cpu sentence-transformers")


class VectorStore:
    def __init__(
        self,
        store_dir:  str   = "memory/vector_store",
        model_name: str   = "all-MiniLM-L6-v2",
        top_k:      int   = 3,
        threshold:  float = 0.30,
    ) -> None:
        faiss, SentenceTransformer = _deps()
        import faiss as _faiss

        self._faiss    = _faiss
        self.top_k     = top_k
        self.threshold = threshold
        self._dir      = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

        self._model    = SentenceTransformer(model_name)
        self._dim      = self._model.get_sentence_embedding_dimension()
        self._idx_path = self._dir / "index.faiss"
        self._met_path = self._dir / "meta.pkl"
        self._index, self._meta = self._load()

    def _load(self):
        if self._idx_path.exists() and self._met_path.exists():
            return self._faiss.read_index(str(self._idx_path)), pickle.loads(self._met_path.read_bytes())
        return self._faiss.IndexFlatIP(self._dim), []  # cosine via normalized IP

    def _save(self):
        self._faiss.write_index(self._index, str(self._idx_path))
        self._met_path.write_bytes(pickle.dumps(self._meta))

    def _embed(self, text: str) -> np.ndarray:
        return self._model.encode([text], normalize_embeddings=True).astype("float32")

    def add(self, text: str, metadata: dict | None = None) -> None:
        self._index.add(self._embed(text))
        self._meta.append({"text": text, "meta": metadata or {}})
        self._save()

    def search(self, query: str) -> list[dict]:
        if self._index.ntotal == 0:
            return []
        k = min(self.top_k, self._index.ntotal)
        scores, ids = self._index.search(self._embed(query), k)
        return [
            {**self._meta[i], "score": float(s)}
            for s, i in zip(scores[0], ids[0])
            if i != -1 and s >= self.threshold
        ]

    def clear(self):
        import faiss as _f
        self._index, self._meta = _f.IndexFlatIP(self._dim), []
        self._save()

    @property
    def size(self) -> int:
        return self._index.ntotal


class LongTermStore:
    def __init__(self, db_path: str = "memory/long_term.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        with sqlite3.connect(db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    content    TEXT NOT NULL,
                    metadata   TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)

    def save(self, fact: str, metadata: dict | None = None) -> None:
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO facts (content, metadata, created_at) VALUES (?,?,?)",
                (fact, json.dumps(metadata or {}), datetime.now(timezone.utc).isoformat()),
            )

    def search(self, query: str, top_k: int = 5) -> list[str]:
        kws = query.lower().split()
        if not kws:
            return []
        clause = " OR ".join(["LOWER(content) LIKE ?"] * len(kws))
        with sqlite3.connect(self.db_path) as c:
            rows = c.execute(
                f"SELECT content FROM facts WHERE {clause} ORDER BY id DESC LIMIT {top_k}",
                [f"%{kw}%" for kw in kws],
            ).fetchall()
        return [r[0] for r in rows]

    def all_facts(self) -> list[str]:
        with sqlite3.connect(self.db_path) as c:
            return [r[0] for r in c.execute("SELECT content FROM facts ORDER BY id").fetchall()]

    def clear(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("DELETE FROM facts")