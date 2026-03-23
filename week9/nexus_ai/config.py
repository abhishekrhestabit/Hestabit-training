"""NEXUS AI runtime configuration.

Mirrors model selection from project-level model.yaml and delegates
actual client creation to config/model_loader.py so both Day 4 and
NEXUS use the same provider/key logic.

Key priority (highest → lowest):
  1. Environment variable  (export GEMINI_API_KEY=...)
  2. .env file             (week9/.env)
  3. model.yaml            (week9/model.yaml)
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)  # .env should win over stale shell exports


# ── Load model.yaml ───────────────────────────────────────────────
def _load_model_yaml() -> dict:
    yaml_path = ROOT / "model.yaml"
    if not yaml_path.exists():
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


_MODEL_CFG = _load_model_yaml()

# ── Active provider ───────────────────────────────────────────────
ACTIVE_PROVIDER = (
    os.environ.get("NEXUS_PROVIDER")
    or _MODEL_CFG.get("active_provider")
    or "ollama"
).lower()

# ── Model names (for display only) ───────────────────────────────
OLLAMA_MODEL = (
    os.environ.get("OLLAMA_MODEL")
    or (_MODEL_CFG.get("ollama") or {}).get("model")
    or "qwen2.5:7b-instruct-q4_K_M"
)
GEMINI_MODEL = (
    os.environ.get("GEMINI_MODEL")
    or (_MODEL_CFG.get("gemini") or {}).get("model")
    or "gemini-3.1-flash-lite-preview"
)

# ── Paths ─────────────────────────────────────────────────────────
NEXUS_DIR  = Path(__file__).resolve().parent
MEMORY_DIR = NEXUS_DIR / "memory_store"
LOG_DIR    = NEXUS_DIR / "logs"
OUTPUT_DIR = NEXUS_DIR / "outputs"

for _d in (MEMORY_DIR, LOG_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Pipeline quality settings ─────────────────────────────────────
MAX_CODE_RETRIES    = 3
MAX_QUALITY_RETRIES = 3
MIN_QUALITY_SCORE   = 7


def get_model_client():
    """
    Create a model client using the shared Day 3 model loader.
    Single source of truth — no duplication of provider logic.
    """
    from config.model_loader import get_model_client as _get
    return _get()