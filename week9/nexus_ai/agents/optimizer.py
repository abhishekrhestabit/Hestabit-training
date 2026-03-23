"""
nexus_ai/agents/optimizer.py  —  Optimizer Agent
Improves output based on Critic feedback.
For code tasks: reads files, rewrites them with improvements, saves back to disk.
For text tasks: rewrites the textual content.
"""

import re
import time
from pathlib import Path
from .base_agent import BaseAgent


class OptimizerAgent(BaseAgent):
    NAME = "Optimizer"
    ROLE = "Improves output — rewrites code files or text based on critic feedback"

    SYSTEM_PROMPT = """\
You are the Optimizer Agent in NEXUS AI.

You receive work that needs improvement and specific instructions on what to fix.

RULES:
  - Address every gap the Critic identified — don't skip any
  - Keep what was good (listed in strengths)
  - Be more thorough, specific, and structured than the original
  - Do NOT just rephrase — actually fix the issues
  - Your output replaces the previous version entirely\
"""

    CODE_IMPROVE_SYS = """\
You are improving Python code based on critic feedback.

You will receive:
  - The original task
  - The current file content
  - Specific gaps and improvement instructions from the Critic

Output ONLY the improved, complete Python code for this file.
No fences. No explanation. Just the complete corrected code.\
"""

    async def run(self, original_output: str, critic_feedback: dict,
                  original_task: str = "") -> str:
        from nexus_ai.logger import log
        t0      = time.time()
        gaps    = "\n".join(f"  - {g}" for g in critic_feedback.get("gaps", []))
        improve = critic_feedback.get("improvement_instructions", "Improve quality.")
        score   = critic_feedback.get("score", 0)
        files_to_fix = critic_feedback.get("files_to_fix", [])

        improved_files = []

        # ── If Critic identified specific files, improve them on disk ──
        if files_to_fix:
            for file_path in files_to_fix:
                p = Path(file_path)
                if not p.exists():
                    continue
                try:
                    current_content = p.read_text(encoding="utf-8")
                    improved_code   = await self._llm(
                        self.CODE_IMPROVE_SYS,
                        f"Original task: {original_task}\n\n"
                        f"File: {file_path}\n"
                        f"Current content:\n{current_content}\n\n"
                        f"Gaps to fix:\n{gaps}\n\n"
                        f"Improvement instructions:\n{improve}\n\n"
                        f"Write the complete improved version of {file_path}:"
                    )
                    # Strip any fences the model added
                    improved_code = re.sub(
                        r"^```[\w]*\n?", "", improved_code, flags=re.MULTILINE
                    )
                    improved_code = re.sub(
                        r"\n?```\s*$", "", improved_code, flags=re.MULTILINE
                    ).strip()

                    p.write_text(improved_code, encoding="utf-8")
                    improved_files.append(file_path)
                    log.info("Optimizer: improved file", path=file_path)
                except Exception as e:
                    log.warn("Optimizer: could not improve file",
                             path=file_path, error=str(e))

        # ── Also scan context for any files Coder created ────────────
        elif original_output:
            pattern = re.compile(
                r'(?:Created|Updated|Wrote)\s+([\w./\-]+\.(?:py|txt|md|yaml|yml))',
            )
            found = pattern.findall(original_output)
            for file_path in found:
                p = Path(file_path)
                if not p.exists() or not file_path.endswith(".py"):
                    continue
                try:
                    current_content = p.read_text(encoding="utf-8")
                    # Only improve if file looks incomplete (under 20 lines)
                    if len(current_content.splitlines()) < 20:
                        improved_code = await self._llm(
                            self.CODE_IMPROVE_SYS,
                            f"Original task: {original_task}\n\n"
                            f"File: {file_path}\n"
                            f"Current content:\n{current_content}\n\n"
                            f"Gaps:\n{gaps}\n\n"
                            f"Instructions:\n{improve}\n\n"
                            f"Write the complete improved version:"
                        )
                        improved_code = re.sub(
                            r"^```[\w]*\n?", "", improved_code, flags=re.MULTILINE
                        )
                        improved_code = re.sub(
                            r"\n?```\s*$", "", improved_code, flags=re.MULTILINE
                        ).strip()
                        p.write_text(improved_code, encoding="utf-8")
                        improved_files.append(file_path)
                        log.info("Optimizer: improved short file", path=file_path)
                except Exception as e:
                    log.warn("Optimizer: file improvement failed",
                             path=file_path, error=str(e))

        # ── Always produce a textual improvement summary ──────────────
        prompt = (
            f"Original task:\n{original_task}\n\n"
            f"Previous output (score {score}/10):\n{original_output[:1000]}\n\n"
            f"Gaps fixed:\n{gaps}\n\n"
            f"Instructions applied:\n{improve}\n\n"
            + (f"Files improved on disk: {', '.join(improved_files)}\n\n"
               if improved_files else "") +
            f"Provide an improved summary of the work done:"
        )
        result = await self._llm(self.SYSTEM_PROMPT, prompt)

        if improved_files:
            result = (
                f"✅ Improved {len(improved_files)} file(s) on disk: "
                f"{', '.join(improved_files)}\n\n{result}"
            )

        log.agent(self.NAME, input_text=improve[:200], output_text=result,
                  duration=time.time() - t0, success=True,
                  extra={"original_score": score,
                         "files_improved": improved_files})
        return result