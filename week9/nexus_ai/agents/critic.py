"""
nexus_ai/agents/critic.py  —  Critic Agent
Reviews output quality — reads actual files on disk for code tasks.
"""

import json, os, re, time
from pathlib import Path
from .base_agent import BaseAgent


class CriticAgent(BaseAgent):
    NAME = "Critic"
    ROLE = "Reviews output quality — reads actual files for code tasks"

    SYSTEM_PROMPT = """\
You are the Critic Agent in NEXUS AI. You review work done by other agents.

Output a JSON object — raw, no fences:
{
  "score": <integer 1-10>,
  "verdict": "pass" | "needs_improvement",
  "strengths": ["..."],
  "gaps": ["specific gap 1", "specific gap 2"],
  "files_to_fix": ["path/to/file.py"],
  "improvement_instructions": "Precise instructions — what to fix and how"
}

SCORING:
  9-10  Excellent — complete, accurate, well-structured, code runs correctly
  7-8   Good — minor gaps, usable as-is
  5-6   Adequate — missing sections or logic errors
  1-4   Poor — incomplete, broken, or off-topic

For CODE tasks: score based on the ACTUAL file contents shown, not descriptions.
Check: imports correct? logic complete? no placeholder comments? runnable?

verdict = "pass" if score >= 7, else "needs_improvement"
Be specific — vague feedback is useless.\
"""

    def _read_files_from_context(self, context: str, task: str) -> str:
        """
        Scan context and task for file paths, read any that exist on disk.
        Returns a string of file contents for Critic to review.
        """
        # Find all file paths mentioned across context + task
        pattern = re.compile(
            r'(?:(?:[\w\-]+/)*)[\w\-]+\.(?:py|txt|md|yaml|yml|json|html|js|ts|css)',
            re.I
        )
        candidates = set(pattern.findall(context + " " + task))

        # Also scan for "Created X" / "Updated X" patterns from Coder output
        created = re.findall(r'(?:Created|Updated|Wrote)\s+([\w./\-]+\.\w+)', context)
        candidates.update(created)

        file_contents = []
        for path_str in sorted(candidates):
            p = Path(path_str)
            if p.exists() and p.is_file():
                try:
                    content = p.read_text(encoding="utf-8")
                    file_contents.append(
                        f"── File: {path_str} ({len(content)} chars) ──\n{content}"
                    )
                except Exception:
                    pass

        return "\n\n".join(file_contents) if file_contents else ""

    async def run(self, instruction: str, context: str = "") -> dict:
        from nexus_ai.logger import log
        t0 = time.time()

        # Read actual files from disk — review real code, not descriptions
        file_contents = self._read_files_from_context(context, instruction)

        review_input = f"Original task:\n{instruction}\n\n"
        if file_contents:
            review_input += f"ACTUAL FILE CONTENTS ON DISK:\n{file_contents}\n\n"
            review_input += "Review the actual code above — score based on what is really there."
        else:
            review_input += f"Work to review (no files found on disk):\n{context}"

        raw = await self._llm(self.SYSTEM_PROMPT, review_input)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        try:
            result = json.loads(raw)
        except Exception:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            result = json.loads(m.group()) if m else {}

        if not result:
            result = {"score": 5, "verdict": "needs_improvement",
                      "gaps": ["Could not parse critic response"],
                      "improvement_instructions": "Review and improve the output."}

        score   = result.get("score", 7)
        verdict = result.get("verdict", "pass")
        files   = result.get("files_to_fix", [])

        log.agent(self.NAME, input_text=instruction[:200], output_text=raw,
                  duration=time.time() - t0, success=True,
                  extra={"score": score, "verdict": verdict,
                         "files_found": len(file_contents) > 0,
                         "files_to_fix": files})
        log.quality_check(score=score, agent="Critic", retry=0)
        return result