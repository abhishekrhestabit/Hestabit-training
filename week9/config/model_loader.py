"""
config/model_loader.py
─────────────────────────────────────────────────────────────────
Reads model.yaml and returns the correct AutoGen 0.7.5
model client.

Usage:
    from config.model_loader import get_model_client
    model_client = get_model_client()
─────────────────────────────────────────────────────────────────
"""

import os
import yaml
from pathlib import Path


def _load_yaml() -> dict:
    """Find and load model.yaml from project root."""
    root = Path(__file__).resolve().parent.parent
    yaml_path = root / "model.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"model.yaml not found at {yaml_path}")
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def get_model_client():
    """
    Returns an AutoGen-compatible model client based on model.yaml.

    active_provider options:
        "ollama"  → OllamaChatCompletionClient  (local, CPU-safe)
        "gemini"  → OpenAIChatCompletionClient  (Google Gemini via REST)
        "groq"    → OpenAIChatCompletionClient  (Groq cloud)
    """
    cfg = _load_yaml()
    provider = cfg.get("active_provider", "ollama").lower()

    # ──────────────────────────────────────────
    #  LOCAL — Ollama / Qwen
    # ──────────────────────────────────────────
    if provider == "ollama":
        from autogen_ext.models.ollama import OllamaChatCompletionClient

        ollama_cfg = cfg["ollama"]
        print(f"[ModelLoader] Using LOCAL Ollama → model: {ollama_cfg['model']}")
        return OllamaChatCompletionClient(
            model=ollama_cfg["model"],
            host=ollama_cfg.get("base_url", "http://localhost:11434"),
            model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": True
        }
        )

    # ──────────────────────────────────────────
    #  API — Google Gemini
    # ──────────────────────────────────────────
    elif provider == "gemini":
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        gemini_cfg = cfg["gemini"]
        api_key = gemini_cfg.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise ValueError(
                "Gemini API key not set. Edit model.yaml or set GEMINI_API_KEY env var."
            )
        print(f"[ModelLoader] Using Gemini API → model: {gemini_cfg['model']}")
        return OpenAIChatCompletionClient(
            model=gemini_cfg["model"],
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model_capabilities={
                "vision": False,
                "function_calling": True,
                "json_output": True,
            },
        )

    # ──────────────────────────────────────────
    #  API — Groq
    # ──────────────────────────────────────────
    elif provider == "groq":
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        groq_cfg = cfg["groq"]
        api_key = groq_cfg.get("api_key") or os.environ.get("GROQ_API_KEY", "")
        if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
            raise ValueError(
                "Groq API key not set. Edit model.yaml or set GROQ_API_KEY env var."
            )
        print(f"[ModelLoader] Using Groq API → model: {groq_cfg['model']}")
        return OpenAIChatCompletionClient(
            model=groq_cfg["model"],
            api_key=api_key,
            base_url=groq_cfg.get("base_url", "https://api.groq.com/openai/v1"),
            model_capabilities={
                "vision": False,
                "function_calling": True,
                "json_output": True,
            },
        )

    else:
        raise ValueError(
            f"Unknown provider '{provider}'. Choose: ollama | gemini | groq"
        )