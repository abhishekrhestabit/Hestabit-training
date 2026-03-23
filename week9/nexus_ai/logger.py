"""
nexus_ai/logger.py
─────────────────────────────────────────────────────────────────
Structured logger for NEXUS AI.

Every agent run is logged with:
  - timestamp
  - agent name
  - input (truncated)
  - output (truncated)
  - duration
  - success/failure

Log files:
  logs/nexus_YYYY-MM-DD.log   ← rotating daily plain-text log
  logs/nexus_trace.jsonl      ← machine-readable JSON lines for debugging

Usage:
    from nexus_ai.logger import log
    log.agent("Researcher", input="...", output="...", duration=1.2)
    log.info("Pipeline started")
    log.error("Agent failed", agent="Coder", error="...")
─────────────────────────────────────────────────────────────────
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path


# ── Setup ─────────────────────────────────────────────────────────

def _setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("nexus_ai")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # already configured

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — rotating daily
    today     = datetime.now().strftime("%Y-%m-%d")
    file_path = log_dir / f"nexus_{today}.log"
    fh = logging.FileHandler(file_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler — INFO and above only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# ── NexusLogger ───────────────────────────────────────────────────

class NexusLogger:
    """
    Thin wrapper around Python logging that also writes
    structured JSON traces for debugging.
    """

    def __init__(self, log_dir: Path):
        self._logger    = _setup_logger(log_dir)
        self._trace_path = log_dir / "nexus_trace.jsonl"
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._task_id    = 0

    # ── Public API ────────────────────────────────────────────────

    def info(self, msg: str, **kwargs):
        self._logger.info(self._fmt(msg, kwargs))

    def warn(self, msg: str, **kwargs):
        self._logger.warning(self._fmt(msg, kwargs))

    def error(self, msg: str, **kwargs):
        self._logger.error(self._fmt(msg, kwargs))

    def debug(self, msg: str, **kwargs):
        self._logger.debug(self._fmt(msg, kwargs))

    def agent(
        self,
        agent_name:  str,
        input_text:  str = "",
        output_text: str = "",
        duration:    float = 0.0,
        success:     bool = True,
        extra:       dict | None = None,
    ):
        """Log a single agent invocation with full trace."""
        self._task_id += 1
        status = "✅" if success else "❌"

        # Human-readable log
        self._logger.info(
            f"{status} [{agent_name}] "
            f"in={len(input_text)}chars | "
            f"out={len(output_text)}chars | "
            f"{duration:.1f}s"
        )

        # Machine-readable JSON trace
        record = {
            "session":    self._session_id,
            "task_id":    self._task_id,
            "ts":         datetime.now().isoformat(),
            "agent":      agent_name,
            "success":    success,
            "duration_s": round(duration, 2),
            "input":      input_text[:500],
            "output":     output_text[:500],
            **(extra or {}),
        }
        self._write_trace(record)

    def pipeline_start(self, query: str):
        self._logger.info(f"{'═'*50}")
        self._logger.info(f"PIPELINE START | query: {query[:100]}")
        self._logger.info(f"{'═'*50}")
        self._write_trace({"event": "pipeline_start", "query": query,
                           "ts": datetime.now().isoformat(),
                           "session": self._session_id})

    def pipeline_end(self, query: str, duration: float, success: bool):
        status = "COMPLETE" if success else "FAILED"
        self._logger.info(f"PIPELINE {status} | {duration:.1f}s | query: {query[:60]}")
        self._write_trace({"event": f"pipeline_{status.lower()}",
                           "query": query, "duration_s": round(duration, 2),
                           "ts": datetime.now().isoformat(),
                           "session": self._session_id})

    def quality_check(self, score: int, agent: str, retry: int):
        self._logger.info(f"QUALITY CHECK | score={score}/10 | agent={agent} | retry={retry}")

    # ── Internal ──────────────────────────────────────────────────

    @staticmethod
    def _fmt(msg: str, kwargs: dict) -> str:
        if kwargs:
            parts = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{msg} | {parts}"
        return msg

    def _write_trace(self, record: dict):
        try:
            with open(self._trace_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass  # never crash the pipeline because of logging


# ── Module-level singleton ────────────────────────────────────────
# Import this in every agent:  from nexus_ai.logger import log

from nexus_ai.config import LOG_DIR
log = NexusLogger(LOG_DIR)