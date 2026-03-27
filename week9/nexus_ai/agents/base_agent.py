"""
nexus_ai/agents/base_agent.py
─────────────────────────────────────────────────────────────────
Base class for all NEXUS agents.

Every agent:
  - Has a name and role description
  - Has a focused system prompt
  - Makes a single LLM call via run()
  - Logs its invocation automatically
  - Returns a plain string result
─────────────────────────────────────────────────────────────────
"""

import time
from autogen_core.models import UserMessage, SystemMessage


RETRYABLE_PROVIDER_SIGNALS = [
    "rate limit",
    "rate_limit",
    "429",
    "quota",
    "resource exhausted",
    "too many requests",
    "503",
    "service unavailable",
    "currently experiencing high demand",
    "unavailable",
    "overloaded",
]


def is_retryable_provider_error(error: Exception) -> bool:
    text = str(error).lower()
    return any(signal in text for signal in RETRYABLE_PROVIDER_SIGNALS)


async def call_model_with_fallback(model_client, system: str, user: str, *, source: str, agent: str):
    from nexus_ai.config import (
        get_fallback_providers,
        get_model_client,
        get_runtime_client,
        get_runtime_provider,
        set_runtime_client,
    )
    from nexus_ai.logger import log

    current_provider = get_runtime_provider()
    providers_to_try = [current_provider] + get_fallback_providers(current_provider)
    attempted = set()
    last_error = None

    for provider in providers_to_try:
        if provider in attempted:
            continue
        attempted.add(provider)

        try:
            client = model_client if provider == current_provider else get_model_client(
                provider_override=provider,
                set_runtime=False,
            )
            if provider != current_provider:
                set_runtime_client(client, provider)
                current_provider = provider
                log.warn("Retrying with fallback provider", agent=agent, provider=provider)
            else:
                client = get_runtime_client()

            response = await client.create(
                messages=[
                    SystemMessage(content=system),
                    UserMessage(content=user, source=source),
                ]
            )
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    p.text if hasattr(p, "text") else str(p) for p in content
                )
            return (content or "").strip(), client
        except Exception as error:
            last_error = error
            if provider == current_provider and not is_retryable_provider_error(error):
                raise
            if not is_retryable_provider_error(error):
                continue

    if last_error:
        raise last_error
    raise RuntimeError("No model provider available.")


class BaseAgent:
    """
    Minimal base for all NEXUS agents.
    Subclasses define NAME, ROLE, and SYSTEM_PROMPT,
    then call super().run() or override run() for tool use.
    """

    NAME:          str = "BaseAgent"
    ROLE:          str = "Generic agent"
    SYSTEM_PROMPT: str = "You are a helpful assistant."

    def __init__(self, model_client):
        self.client = model_client

    async def _llm(self, system: str, user: str) -> str:
        """Single focused LLM call."""
        result, client = await call_model_with_fallback(
            self.client,
            system,
            user,
            source=self.NAME,
            agent=self.NAME,
        )
        self.client = client
        return result

    async def run(self, prompt: str, context: str = "") -> str:
        """
        Run this agent. Override in subclasses for tool use.
        Returns a plain string result.
        """
        from nexus_ai.logger import log
        t0    = time.time()
        user  = f"{prompt}\n\nContext:\n{context}" if context else prompt
        try:
            result = await self._llm(self.SYSTEM_PROMPT, user)
            log.agent(self.NAME, input_text=prompt, output_text=result,
                      duration=time.time() - t0, success=True)
            return result
        except Exception as e:
            log.agent(self.NAME, input_text=prompt, output_text=str(e),
                      duration=time.time() - t0, success=False,
                      extra={"error": str(e)})
            raise
