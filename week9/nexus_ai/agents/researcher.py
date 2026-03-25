"""
nexus_ai/agents/researcher.py  —  Researcher Agent
Web search (DuckDuckGo) + file reading. Gathers information for other agents.
"""

import subprocess, sys, re
from .base_agent import BaseAgent


def web_search(query: str, max_results: int = 6) -> str:
    """DuckDuckGo search via ddgs package."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"Title:   {r.get('title', '')}\n"
                    f"URL:     {r.get('href', '')}\n"
                    f"Snippet: {r.get('body', '')}\n"
                )
        if not results:
            return "No results found — DDG returned empty results."
        try:
            from nexus_ai.logger import log
            log.info(f"DDG returned {len(results)} results", query=query[:60])
        except Exception:
            pass
        return "\n---\n".join(results)
    except Exception as e:
        return f"[web_search ERROR] {e}"


class ResearcherAgent(BaseAgent):
    NAME = "Researcher"
    ROLE = "Gathers information via web search and file reading"
    SYSTEM_PROMPT = """\
You are the Researcher Agent in NEXUS AI.

You gather information to answer a research question.
You have access to web search results and file contents provided in context.

RULES:
  - Synthesise information from the provided sources
  - Be factual and specific — cite what you found
  - If web results are provided, use them; don't make up facts
  - Structure your findings clearly with sections
  - Keep it focused on what was asked\
"""

    async def run(self, instruction: str, context: str = "",
                  file_path: str | None = None) -> str:
        from nexus_ai.logger import log
        import time
        t0 = time.time()

        research_ctx = context

        # File reading — always do this first, before web search
        # Pass the actual file content to the LLM so it can analyse it
        if file_path:
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
                from tools.file_agent import read_txt, read_csv, read_json
                fp = file_path.lower()
                if fp.endswith(".csv"):
                    from tools.file_agent import read_file
                    content = read_file(file_path)
                elif fp.endswith(".json"):
                    import json
                    result = read_json(file_path)
                    content = json.dumps(result["data"], indent=2) if result["success"] else result["error"]
                else:
                    content = read_txt(file_path)
                research_ctx += f"\n\n── File contents: {file_path} ──\n{content}"
                log.info("Researcher: read file", path=file_path, chars=len(content))
            except Exception as e:
                research_ctx += f"\n\n[Could not read {file_path}: {e}]"
                log.warn("Researcher: file read failed", path=file_path, error=str(e))

        # Web search — only when genuinely needed
        # Skip if memory context already contains relevant data for follow-up questions
        if not file_path:
            memory_has_data = len(research_ctx) > 300  # memory was recalled

            # Follow-up / recommendation questions — answer from memory, no search needed
            is_followup = any(w in instruction.lower() for w in [
                "should i", "which should", "what should", "suggest",
                "recommend", "which one", "what do you think", "based on",
                "given that", "for me", "in my case", "what would you",
            ])

            # Needs fresh web data
            needs_search = any(w in instruction.lower() for w in [
                # Research/analysis
                "research", "find", "search", "information about",
                "latest", "current state", "compare", "top 5",
                "best models", "documentation", "docs", "reference",
                # Factual questions that need current data
                "who won", "who is", "who are", "who was",
                "what won", "what is the", "what are the", "what happened",
                "which team", "which country", "which player",
                "when did", "when was", "when is",
                "where is", "where was",
                "how many", "how much", "how did",
                "result", "score", "winner", "champion", "championship",
                "tournament", "match", "game", "election", "president",
                "ceo", "founder", "released", "launch", "announced",
                "news", "update", "status",
            ])

            # Only search if it's a genuine research need AND not a follow-up
            search_trigger = needs_search and not (memory_has_data and is_followup)

            if search_trigger:
                from datetime import datetime
                current_year = datetime.now().year

                # Strip stale year references from instruction and replace with current year
                # e.g. "2024-2025 trends" → "2026 trends"
                import re as _re
                query = instruction[:150]
                query = _re.sub(r'\b20(2[0-5])\b', str(current_year), query)
                query = _re.sub(r'\b20(2[0-5])-20(2[0-5])\b', str(current_year), query)

                # Append current year if the query mentions "latest", "current", "trends"
                # and doesn't already have the current year
                time_words = ["latest", "current", "recent", "trends", "now", "today"]
                if any(w in query.lower() for w in time_words) and str(current_year) not in query:
                    query = query.rstrip(".") + f" {current_year}"

                log.info("Researcher: web search", query=query[:80])
                results = web_search(query, max_results=4)
                research_ctx += f"\n\n── Web Search Results ({current_year}) ──\n{results}"
            elif memory_has_data and is_followup:
                log.info("Researcher: using memory context (follow-up question)")

        from datetime import datetime
        current_year = datetime.now().year
        today_str    = datetime.now().strftime("%B %d, %Y")

        # Inject date into system prompt so LLM knows the current year
        system = (
            f"Today's date is {today_str}. "
            f"When discussing current events, always reference {current_year}.\n\n"
            + self.SYSTEM_PROMPT
        )

        # If web results were retrieved, make the LLM use them explicitly
        if "── Web Search Results" in research_ctx:
            user_prompt = (
                f"Instruction:\n{instruction}\n\n"
                f"Sources and context:\n{research_ctx}\n\n"
                f"IMPORTANT: Web search results are provided above. "
                f"Base your answer PRIMARILY on these search results, not on prior training knowledge. "
                f"If the results contain a definitive answer, state it clearly and directly. "
                f"Provide a comprehensive, detailed response — do not summarise too briefly."
            )
        else:
            user_prompt = f"Instruction:\n{instruction}\n\nSources and context:\n{research_ctx}"

        result = await self._llm(system, user_prompt)
        log.agent(self.NAME, input_text=instruction, output_text=result,
                  duration=time.time() - t0, success=True)
        return result
