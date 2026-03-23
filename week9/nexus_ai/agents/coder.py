"""
nexus_ai/agents/coder.py  —  Coder Agent
Writes and executes Python code. Uses Day 3 code_executor tools.
"""

import re, time
from .base_agent import BaseAgent


class CoderAgent(BaseAgent):
    NAME = "Coder"
    ROLE = "Writes and executes Python code"
    SYSTEM_PROMPT = """\
You are the Coder Agent in NEXUS AI.

You write complete, runnable Python code to accomplish goals.

RULES:
  - Write complete code — all imports included
  - Use print() for every output
  - Any library is available — missing packages are auto-installed
  - After writing code, it will be executed automatically
  - Report what the code does and what the output means\
"""

    CODE_GEN_SYS = """\
Write complete runnable Python code for the goal below.
Use print() for all output. Any library OK — packages auto-install.
Output ONLY raw Python code. No fences. No explanation.

CRITICAL RULES:
  - If the goal is to CREATE FILES (API, backend, scripts, configs):
      Write code that uses open() to write the files to disk, then print confirmation.
      Do NOT start a server. Do NOT call uvicorn.run() or app.run().
      The code must finish and exit on its own.
  - If the goal is to RUN CALCULATIONS or ANALYSE DATA:
      Write code that computes and prints results, then exits.
  - NEVER write infinite loops or blocking server calls (uvicorn, flask run, etc.).\
"""

    async def run(self, instruction: str, context: str = "") -> str:
        from tools.code_executor import execute_python_code, auto_install_missing
        from nexus_ai.logger import log
        t0 = time.time()

        # Generate code
        code = await self._llm(
            self.CODE_GEN_SYS,
            f"Goal: {instruction}\n\nContext from previous agents:\n{context}",
        )
        code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()
        log.debug("Coder: generated code", lines=len(code.splitlines()))

        # Execute with retries
        for attempt in range(1, 4):
            auto_install_missing(code)
            result = execute_python_code(code)
            if result["success"]:
                output = result["stdout"] or "(no output)"
                log.agent(self.NAME, input_text=instruction, output_text=output,
                          duration=time.time() - t0, success=True,
                          extra={"attempts": attempt})
                return f"Code executed successfully.\n\nOutput:\n{output}"

            error = (result["error"] or result["stderr"] or "unknown").strip()
            log.warn(f"Coder attempt {attempt} failed", error=error[:100])

            if attempt == 3:
                log.agent(self.NAME, input_text=instruction, output_text=error,
                          duration=time.time() - t0, success=False)
                return f"Code execution failed after 3 attempts.\nLast error: {error}"

            # Regenerate with error context
            code = await self._llm(
                self.CODE_GEN_SYS,
                f"Goal: {instruction}\n\nContext:\n{context}\n\n"
                f"Previous attempt failed:\n{error}\n\nFailed code:\n{code}\n\n"
                f"Write a corrected version:",
            )
            code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()

        return "Coder failed."