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
DEFAULT_MODELS = {
    "ollama": "qwen2.5:7b-instruct-q4_K_M",
    "gemini": "gemini-3.1-flash-lite-preview",
    "groq": "llama-3.3-70b-versatile",
}


def _get_model_name(provider: str) -> str:
    provider_cfg = _MODEL_CFG.get(provider) or {}
    return (
        os.environ.get(f"{provider.upper()}_MODEL")
        or provider_cfg.get("model")
        or DEFAULT_MODELS[provider]
    )


OLLAMA_MODEL = _get_model_name("ollama")
GEMINI_MODEL = _get_model_name("gemini")
GROQ_MODEL   = _get_model_name("groq")
ACTIVE_MODEL = _get_model_name(ACTIVE_PROVIDER) if ACTIVE_PROVIDER in DEFAULT_MODELS else "unknown"

# ── Paths ─────────────────────────────────────────────────────────
NEXUS_DIR  = Path(__file__).resolve().parent
MEMORY_DIR = NEXUS_DIR / "memory_store"
LOG_DIR    = NEXUS_DIR / "logs"
OUTPUT_DIR = NEXUS_DIR / "outputs"
WORKSPACE_DIR = ROOT / "workspace"

for _d in (MEMORY_DIR, LOG_DIR, OUTPUT_DIR, WORKSPACE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Pipeline quality settings ─────────────────────────────────────
MAX_CODE_RETRIES    = 3
MAX_QUALITY_RETRIES = 3
MIN_QUALITY_SCORE   = 7
POST_VALIDATION_REPLAN_MAX_SCORE = 5

FALLBACK_PROVIDER_ORDER = {
    "groq": ("gemini", "ollama"),
    "gemini": ("groq", "ollama"),
    "ollama": (),
}

_RUNTIME_PROVIDER = ACTIVE_PROVIDER
_RUNTIME_CLIENT   = None


def get_runtime_provider() -> str:
    return _RUNTIME_PROVIDER


def get_runtime_model() -> str:
    provider = get_runtime_provider()
    return _get_model_name(provider) if provider in DEFAULT_MODELS else "unknown"


def set_runtime_client(client, provider: str) -> None:
    global _RUNTIME_CLIENT, _RUNTIME_PROVIDER
    _RUNTIME_CLIENT = client
    _RUNTIME_PROVIDER = provider.lower()


def get_fallback_providers(current_provider: str | None = None) -> list[str]:
    provider = (current_provider or get_runtime_provider() or ACTIVE_PROVIDER).lower()
    ordered = []
    seen = {provider}

    for candidate in FALLBACK_PROVIDER_ORDER.get(provider, ()):
        if candidate not in seen:
            ordered.append(candidate)
            seen.add(candidate)

    extra = os.environ.get("NEXUS_FALLBACK_PROVIDERS", "").strip()
    if extra:
        for candidate in [p.strip().lower() for p in extra.split(",") if p.strip()]:
            if candidate in DEFAULT_MODELS and candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)

    return ordered


def get_model_client(provider_override: str | None = None, *, set_runtime: bool = True):
    """
    Create a model client using the shared Day 3 model loader.
    Single source of truth — no duplication of provider logic.
    """
    from config.model_loader import get_model_client as _get
    provider = (provider_override or get_runtime_provider() or ACTIVE_PROVIDER).lower()
    client = _get(provider_override=provider)
    if set_runtime:
        set_runtime_client(client, provider)
    return client


def get_runtime_client():
    global _RUNTIME_CLIENT
    if _RUNTIME_CLIENT is None:
        _RUNTIME_CLIENT = get_model_client(set_runtime=True)
    return _RUNTIME_CLIENT


def switch_to_fallback_provider(current_provider: str | None = None):
    from nexus_ai.logger import log

    provider = (current_provider or get_runtime_provider() or ACTIVE_PROVIDER).lower()
    errors = []

    for candidate in get_fallback_providers(provider):
        try:
            client = get_model_client(candidate, set_runtime=False)
            set_runtime_client(client, candidate)
            log.warn("Switched model provider", from_provider=provider, to_provider=candidate)
            return candidate, client
        except Exception as e:
            errors.append(f"{candidate}: {e}")

    raise RuntimeError(
        f"No fallback provider available after '{provider}'. "
        + (" | ".join(errors) if errors else "No fallback providers configured.")
    )
