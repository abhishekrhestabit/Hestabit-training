from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from autogen_core.models import ChatCompletionClient, ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient

from .gemini_client import build_gemini_client

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
MODEL_CONFIG_PATH = Path(__file__).resolve().with_name("models.yaml")


def _load_environment() -> None:
    load_dotenv(ENV_PATH, override=True)


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    with MODEL_CONFIG_PATH.open("r", encoding="utf-8") as file:
        registry = yaml.safe_load(file) or {}

    if "providers" not in registry or not isinstance(registry["providers"], dict):
        raise ValueError(f"Invalid model registry in {MODEL_CONFIG_PATH}")

    return registry


def _resolve_family(family_name: str) -> ModelFamily:
    try:
        return getattr(ModelFamily, family_name.upper())
    except AttributeError as exc:
        raise ValueError(f"Unsupported model family '{family_name}' in {MODEL_CONFIG_PATH}") from exc


def _resolve_model_info(model_info: dict[str, Any]) -> dict[str, Any]:
    if not model_info:
        raise ValueError("Each provider must define model_info.")

    resolved = dict(model_info)
    family = resolved.get("family", "UNKNOWN")
    if isinstance(family, str):
        resolved["family"] = _resolve_family(family)
    return resolved


def _resolve_required_value(settings: dict[str, Any], key: str) -> str:
    value = settings.get(key)
    env_key = settings.get(f"{key}_env")

    if value is None and env_key:
        value = os.getenv(env_key)

    if value is None:
        raise ValueError(
            f"Provider '{settings['provider']}' is missing {key}. "
            f"Set {env_key or key} in .env."
        )

    return value


def get_provider_settings(provider: str | None = None) -> dict[str, Any]:
    _load_environment()
    registry = _load_registry()

    provider_name = provider or os.getenv("MODEL_PROVIDER") or registry.get("default_provider")
    providers = registry["providers"]

    if provider_name not in providers:
        available = ", ".join(sorted(providers))
        raise ValueError(f"Unknown provider '{provider_name}'. Available providers: {available}")

    settings = dict(providers[provider_name])
    settings["provider"] = provider_name
    return settings


def _build_openai_client(settings: dict[str, Any], model_info: dict[str, Any], **overrides: Any) -> ChatCompletionClient:
    client_kwargs: dict[str, Any] = {
        "model": settings["model"],
        "api_key": _resolve_required_value(settings, "api_key"),
        "model_info": model_info,
        "parallel_tool_calls": settings.get("parallel_tool_calls", False),
    }

    base_url = settings.get("base_url")
    base_url_env = settings.get("base_url_env")
    if base_url_env:
        base_url = os.getenv(base_url_env, base_url)
    if base_url:
        client_kwargs["base_url"] = base_url

    if "add_name_prefixes" in settings:
        client_kwargs["add_name_prefixes"] = settings["add_name_prefixes"]
    if "include_name_in_message" in settings:
        client_kwargs["include_name_in_message"] = settings["include_name_in_message"]

    client_kwargs.update(overrides)
    return OpenAIChatCompletionClient(**client_kwargs)


def get_model_client(provider: str | None = None, **overrides: Any) -> ChatCompletionClient:
    settings = get_provider_settings(provider)
    model_info = _resolve_model_info(settings["model_info"])
    client_type = settings.get("client_type", "openai")

    if client_type == "semantic-kernel-google":
        gemini_settings = dict(settings)
        gemini_settings["api_key"] = _resolve_required_value(settings, "api_key")
        return build_gemini_client(gemini_settings, model_info, **overrides)

    if client_type == "openai":
        return _build_openai_client(settings, model_info, **overrides)

    raise ValueError(f"Unsupported client_type '{client_type}'")


def describe_active_model(provider: str | None = None) -> str:
    settings = get_provider_settings(provider)
    return f"{settings['provider']} / {settings['model']}"
