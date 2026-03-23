"""
nexus_ai/agents/reporter.py  —  Reporter Agent
Writes the final structured report/answer from all agent outputs.
"""

import time
from pathlib import Path
from .base_agent import BaseAgent


class ReporterAgent(BaseAgent):
    NAME = "Reporter"
    ROLE = "Writes the final structured answer or report"
    SYSTEM_PROMPT = """\
You are the Reporter Agent in NEXUS AI. You write the final answer.

You receive the validated output from all previous agents and write
a clean, well-structured final response for the user.

FORMAT based on task type:
  research/planning  → Markdown report with # Title, ## Sections, bullet points
  code               → Explanation of what was built + the output/result
  analysis           → Executive summary → Key findings → Recommendations
  general            → Clear, direct answer with supporting detail

RULES:
  - Be thorough but not padded — every sentence must add value
  - Use Markdown formatting for structure
  - Start directly with the content — no "Here is your report:" preamble
  - End with a ## Summary or ## Next Steps section\
"""

    async def run(self, instruction: str, context: str = "",
                  save_to: str | None = None) -> str:
        from nexus_ai.logger import log
        t0 = time.time()

        result = await self._llm(
            self.SYSTEM_PROMPT,
            f"Task:\n{instruction}\n\nAll agent findings:\n{context}",
        )

        # Optionally save report to file
        if save_to:
            try:
                from tools.file_agent import write_txt
                Path(save_to).parent.mkdir(parents=True, exist_ok=True)
                write_txt(save_to, result)
                log.info("Reporter: saved to file", path=save_to)
            except Exception as e:
                log.warn("Reporter: could not save file", error=str(e))

        log.agent(self.NAME, input_text=instruction[:200], output_text=result,
                  duration=time.time() - t0, success=True)
        return result