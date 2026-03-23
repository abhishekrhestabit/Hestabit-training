"""
memory/session_memory.py
─────────────────────────────────────────────────────────────────
Short-term (session) memory — lives in RAM for the current run.

Stores the full conversation as a list of turns:
    {"role": "user"|"assistant", "content": "...", "timestamp": ...}

Resets when the process exits — intentionally ephemeral.

Used by Day 4 pipeline to:
    • Build a rolling context window for the LLM
    • Show conversation history to the user
    • Feed summaries into long-term memory
─────────────────────────────────────────────────────────────────
"""

import time
from dataclasses import dataclass, field
from typing import Literal


# ─────────────────────────────────────────────────────────────────
#  Data structures
# ─────────────────────────────────────────────────────────────────

@dataclass
class Turn:
    role:      Literal["user", "assistant"]
    content:   str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "role":      self.role,
            "content":   self.content,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────
#  SessionMemory
# ─────────────────────────────────────────────────────────────────

class SessionMemory:
    """
    In-RAM conversation store.

    Args:
        window: Max number of turns to keep in context.
                Older turns are dropped (but NOT deleted — they stay
                in the full history for summarisation).
    """

    def __init__(self, window: int = 10):
        self._turns:  list[Turn] = []
        self._window: int        = window

    # ── Write ─────────────────────────────────────────────────────

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        """Add a turn to memory."""
        self._turns.append(Turn(role=role, content=content))

    def add_user(self, content: str)      -> None: self.add("user",      content)
    def add_assistant(self, content: str) -> None: self.add("assistant", content)

    # ── Read ──────────────────────────────────────────────────────

    def get_window(self) -> list[dict]:
        """Return the last `window` turns as a list of dicts."""
        return [t.to_dict() for t in self._turns[-self._window:]]

    def get_all(self) -> list[dict]:
        """Return the complete conversation history."""
        return [t.to_dict() for t in self._turns]

    def get_context_string(self, max_chars_per_turn: int = 500) -> str:
        """
        Return the last `window` turns as a plain string for prompt injection.
        Full content is stored in memory — this caps each turn for prompt size.
        Set max_chars_per_turn=None to return full content.
        """
        lines = []
        for t in self._turns[-self._window:]:
            prefix  = "User" if t.role == "user" else "Assistant"
            content = t.content
            if max_chars_per_turn and len(content) > max_chars_per_turn:
                content = content[:max_chars_per_turn] + "... [truncated for context]"
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def recall_context(self, full: bool = False) -> str:
        """
        Return session context formatted for prompt injection.

        full=False (default): caps each turn at 500 chars — use for new tasks
                              where only a summary of history is needed.
        full=True:            returns complete stored content — use for follow-up
                              questions that reference the previous answer directly.
        """
        ctx = self.get_context_string(
            max_chars_per_turn=None if full else 500
        )
        if not ctx:
            return ""
        return f"── Recent conversation ──\n{ctx}"

    def get_recent_user_queries(self, n: int = 5) -> list[str]:
        """Return the last n user queries."""
        return [
            t.content for t in self._turns
            if t.role == "user"
        ][-n:]

    # ── Inspect ───────────────────────────────────────────────────

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    @property
    def is_empty(self) -> bool:
        return len(self._turns) == 0

    def clear(self) -> None:
        """Wipe all turns (start fresh session)."""
        self._turns.clear()

    def display(self) -> None:
        """Print the full session to stdout for debugging."""
        print(f"\n── Session Memory ({self.turn_count} turns) ──")
        for i, t in enumerate(self._turns, 1):
            prefix = "👤 User" if t.role == "user" else "🤖 Agent"
            print(f"  [{i}] {prefix}: {t.content[:120]}")
        print()