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
        response = await self.client.create(
            messages=[
                SystemMessage(content=system),
                UserMessage(content=user, source=self.NAME),
            ]
        )
        content = response.content
        if isinstance(content, list):
            content = " ".join(
                p.text if hasattr(p, "text") else str(p) for p in content
            )
        return (content or "").strip()

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