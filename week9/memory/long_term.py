"""
memory/long_term.py
─────────────────────────────────────────────────────────────────
Long-term memory backed by SQLite.

Stores summarised facts that should survive across sessions:
    • Key facts extracted from conversations
    • Task results worth remembering
    • User preferences / recurring topics

Schema:
    facts(
        id        INTEGER PRIMARY KEY,
        fact      TEXT NOT NULL,
        source    TEXT,          -- "user_query" | "task_result" | "manual"
        tags      TEXT,          -- comma-separated
        created   REAL,          -- unix timestamp
        accessed  REAL           -- last time this fact was retrieved
    )

The database file is: memory/long_term.db
─────────────────────────────────────────────────────────────────
"""

import sqlite3
import time
from pathlib import Path


# ─────────────────────────────────────────────────────────────────
#  LongTermMemory
# ─────────────────────────────────────────────────────────────────

class LongTermMemory:
    """
    SQLite-backed persistent fact store.

    Args:
        db_path: Path to the .db file. Created automatically if missing.
    """

    def __init__(self, db_path: str = "memory/long_term.db"):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        self._init_schema()
        print(f"[LongTermMemory] DB: {self._db_path}  ({self.count} facts stored)")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact     TEXT    NOT NULL,
                    source   TEXT    DEFAULT 'manual',
                    tags     TEXT    DEFAULT '',
                    created  REAL    NOT NULL,
                    accessed REAL    NOT NULL
                )
            """)
            conn.commit()

    # ── Write ─────────────────────────────────────────────────────

    def store(
        self,
        fact:   str,
        source: str       = "manual",
        tags:   list[str] | None = None,
    ) -> int:
        """
        Store a fact. Returns the row id.

        Args:
            fact:   The text of the fact to remember.
            source: Where it came from ("user_query", "task_result", "manual").
            tags:   Optional list of keyword tags for filtering.
        """
        now = time.time()
        tags_str = ",".join(tags or [])
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO facts (fact, source, tags, created, accessed) "
                "VALUES (?, ?, ?, ?, ?)",
                (fact, source, tags_str, now, now),
            )
            conn.commit()
            return cur.lastrowid

    def store_many(self, facts: list[str], source: str = "task_result") -> None:
        """Store multiple facts at once."""
        now = time.time()
        rows = [(f, source, "", now, now) for f in facts if f.strip()]
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO facts (fact, source, tags, created, accessed) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()

    def store_episode(self, query: str, answer: str) -> None:
        """
        Store a completed query+answer pair as two episodic facts.
        Called by the pipeline after every successful run.
        """
        summary = answer[:300] + ("..." if len(answer) > 300 else "")
        self.store(f"User asked: {query[:200]}", source="episode", tags=["query"])
        self.store(f"Agent answered: {summary}",  source="episode", tags=["answer"])

    # ── Read ──────────────────────────────────────────────────────

    def get_recent(self, n: int = 10) -> list[dict]:
        """Return the n most recently stored facts."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM facts ORDER BY created DESC LIMIT ?", (n,)
            ).fetchall()
        return [dict(r) for r in rows]

    def search_by_keyword(self, keyword: str, limit: int = 5) -> list[dict]:
        """
        Simple keyword search across fact text.
        For semantic search use VectorStore.search() instead.
        """
        pattern = f"%{keyword}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE fact LIKE ? "
                "ORDER BY created DESC LIMIT ?",
                (pattern, limit),
            ).fetchall()
            # Update accessed timestamp
            ids = [r["id"] for r in rows]
            if ids:
                conn.execute(
                    f"UPDATE facts SET accessed=? WHERE id IN "
                    f"({','.join('?' * len(ids))})",
                    [time.time()] + ids,
                )
            conn.commit()
        return [dict(r) for r in rows]

    def get_by_source(self, source: str, limit: int = 20) -> list[dict]:
        """Return facts filtered by source."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE source=? ORDER BY created DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_as_context(self, keyword: str = "", n: int = 5) -> str:
        """
        Return relevant facts as a plain string for prompt injection.
        Uses keyword search if provided, else returns most recent.
        """
        facts = (
            self.search_by_keyword(keyword, limit=n)
            if keyword
            else self.get_recent(n=n)
        )
        if not facts:
            return ""
        lines = ["── Long-term memory ──"]
        for f in facts:
            lines.append(f"  • {f['fact']}")
        return "\n".join(lines)

    # ── Inspect ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    def display(self, n: int = 10) -> None:
        """Print the most recent facts."""
        print(f"\n── Long-Term Memory ({self.count} facts) ──")
        for f in self.get_recent(n):
            print(f"  [{f['id']}] ({f['source']}) {f['fact'][:120]}")
        print()

    def clear(self) -> None:
        """Delete all stored facts."""
        with self._connect() as conn:
            conn.execute("DELETE FROM facts")
            conn.commit()
        print("[LongTermMemory] Cleared all facts.")