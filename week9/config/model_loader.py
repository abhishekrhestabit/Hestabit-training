"""
config/model_loader.py
─────────────────────────────────────────────────────────────────
Single source of truth for model client creation.
Used by Day 3, Day 4, and NEXUS AI.

Key priority (highest → lowest):
  1. Environment variable   export GEMINI_API_KEY=...
  2. week9/.env file        GEMINI_API_KEY=...
  3. model.yaml             gemini.api_key: ...

Usage:
    from config.model_loader import get_model_client
    client = get_model_client()
─────────────────────────────────────────────────────────────────
"""

import os
import yaml
from pathlib import Path

# Load .env from project root (week9/.env) — safe, no-op if missing
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass  # python-dotenv not installed — keys must be in env or model.yaml


def _build_model_info(family: str = "unknown") -> dict:
    """Shared AutoGen model metadata for custom/non-native providers."""
    return {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": family,
        "structured_output": True,
        "multiple_system_messages": True,
    }


def _infer_family(provider: str, model: str) -> str:
    """
    Best-effort family mapping for AutoGen.
    Falls back to "unknown" for preview/custom names.
    """
    from autogen_core.models import ModelFamily

    normalized = model.lower()

    if provider == "gemini":
        if "gemini-2.5-flash" in normalized:
            return ModelFamily.GEMINI_2_5_FLASH
        if "gemini-2.5-pro" in normalized:
            return ModelFamily.GEMINI_2_5_PRO
        if "gemini-2.0-flash" in normalized:
            return ModelFamily.GEMINI_2_0_FLASH
        return ModelFamily.UNKNOWN

    if provider == "groq":
        if "llama-3.3-70b" in normalized:
            return ModelFamily.LLAMA_3_3_70B
        if "llama-3.3-8b" in normalized:
            return ModelFamily.LLAMA_3_3_8B
        if "llama-4-maverick" in normalized:
            return ModelFamily.LLAMA_4_MAVERICK
        if "llama-4-scout" in normalized:
            return ModelFamily.LLAMA_4_SCOUT
        return ModelFamily.UNKNOWN

    return ModelFamily.UNKNOWN


def _load_yaml() -> dict:
    root      = Path(__file__).resolve().parent.parent
    yaml_path = root / "model.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"model.yaml not found at {yaml_path}")
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_key(yaml_value: str | None, env_var: str, label: str) -> str:
    """
    Resolve an API key with priority: env var > yaml value.

    Handles three yaml patterns:
      api_key: GEMINI_API_KEY          ← treat as env var name
      api_key: ${GEMINI_API_KEY}       ← shell-style variable
      api_key: actual_key_value        ← literal key (not recommended)
    """
    PLACEHOLDERS = {"", "YOUR_GEMINI_API_KEY_HERE", "YOUR_GROQ_API_KEY_HERE",
                    "YOUR_TAVILY_API_KEY_HERE"}

    # 1. Always check actual env var first (set by .env or export)
    key = os.environ.get(env_var, "")
    if key and key not in PLACEHOLDERS:
        return key

    # 2. Check yaml value
    if yaml_value:
        # Strip shell-style ${...} wrapper
        raw = yaml_value.strip()
        if raw.startswith("${") and raw.endswith("}"):
            raw = raw[2:-1]

        # If value looks like an env var name (ALL_CAPS_WITH_UNDERSCORES)
        # treat it as a reference and look it up
        import re as _re
        if _re.match(r'^[A-Z][A-Z0-9_]+$', raw):
            resolved = os.environ.get(raw, "")
            if resolved and resolved not in PLACEHOLDERS:
                return resolved
        elif raw not in PLACEHOLDERS:
            # Literal key value in yaml
            return raw

    raise ValueError(
        f"{label} API key not set.\n"
        f"Options (any of these work):\n"
        f"  1. week9/.env file:    {env_var}=your_key\n"
        f"  2. Export env var:     export {env_var}=your_key\n"
        f"  3. model.yaml:         api_key: {env_var}  (references env var)\n"
        f"                      or api_key: your_actual_key"
    )


def get_model_client(provider_override: str | None = None):
    """
    Returns an AutoGen 0.7.5 compatible model client based on model.yaml.
    Supports: ollama | gemini | groq
    """
    cfg      = _load_yaml()
    provider = (
        provider_override
        or os.environ.get("NEXUS_PROVIDER")
        or cfg.get("active_provider", "ollama")
    ).lower()

    # ── Ollama (local) ────────────────────────────────────────────
    if provider == "ollama":
        from autogen_ext.models.ollama import OllamaChatCompletionClient
        ollama_cfg = cfg.get("ollama", {})
        model      = (os.environ.get("OLLAMA_MODEL")
                      or ollama_cfg.get("model", "qwen2.5:7b-instruct-q4_K_M"))
        base_url   = (os.environ.get("OLLAMA_BASE_URL")
                      or ollama_cfg.get("base_url", "http://localhost:11434"))
        print(f"[ModelLoader] Using LOCAL Ollama → model: {model}")
        return OllamaChatCompletionClient(
            model=model,
            host=base_url,
            model_info=_build_model_info(),
        )

    # ── Gemini ────────────────────────────────────────────────────
    elif provider == "gemini":
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        gemini_cfg = cfg.get("gemini", {})
        model      = (os.environ.get("GEMINI_MODEL")
                      or gemini_cfg.get("model", "gemini-2.0-flash"))
        api_key    = _resolve_key(
            gemini_cfg.get("api_key"), "GEMINI_API_KEY", "Gemini"
        )
        print(f"[ModelLoader] Using Gemini API → model: {model}")
        return OpenAIChatCompletionClient(
            model=model,
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model_info=_build_model_info(_infer_family("gemini", model)),
        )


    # ── Groq ──────────────────────────────────────────────────────
    elif provider == "groq":
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        groq_cfg = cfg.get("groq", {})
        model    = (os.environ.get("GROQ_MODEL")
                    or groq_cfg.get("model", "llama-3.3-70b-versatile"))
        api_key  = _resolve_key(
            groq_cfg.get("api_key"), "GROQ_API_KEY", "Groq"
        )
        print(f"[ModelLoader] Using Groq API → model: {model}")
        return OpenAIChatCompletionClient(
            model=model,
            api_key=api_key,
            base_url=groq_cfg.get("base_url", "https://api.groq.com/openai/v1"),
            model_info=_build_model_info(_infer_family("groq", model)),
        )

    else:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Set active_provider to: ollama | gemini | groq"
        )
