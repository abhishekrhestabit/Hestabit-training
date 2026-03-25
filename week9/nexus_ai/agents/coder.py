import re, time
from .base_agent import BaseAgent


class CoderAgent(BaseAgent):
    NAME = "Coder"
    ROLE = "Writes and executes Python code"

    SYSTEM_PROMPT = """\
You are the Coder Agent in NEXUS AI.

You write complete, runnable Python code.

RULES:
- Use print() for outputs
- Any library allowed
- Code executes automatically
- Prefer complete, production-leaning implementations over tiny stubs
- For backend/system tasks, create the full module set needed by the task
- Do not add demo data, fake example tasks, or unrelated features unless asked

CRITICAL SAFETY RULES:
- You may ONLY access files explicitly provided or inside ./workspace/
- NEVER access parent directories (../) or system paths
- NEVER delete files
- If a file is provided, use it directly — do not guess paths\
"""

    CODE_GEN_SYS = """\
Write complete runnable Python code.
Use print() for output.

CRITICAL:
- If working with a file, use the exact file path provided in context
- If context provides a task workspace directory, write ALL generated files there
- Do NOT guess file paths
- Do NOT access other files
- Do NOT use parent directories
- If creating files, write only inside ./workspace/
- Never create nested ./workspace/workspace paths
- For backend/API tasks, do not stop at one small file if multiple modules are needed
- For "full system" or "full backend" requests, create complete modules with real logic, validation, and error handling
- Avoid placeholder comments, one-line stubs, or files whose real logic lives only in the temporary execution script
- Do not include uvicorn/flask run blocks unless explicitly requested
- After writing files, print a clear manifest of every created/updated file path

Output ONLY raw Python code.\
"""

    def _is_safe(self, code: str, allowed_files: list, allowed_workspace: str | None = None):
        issues = []

        # Block dangerous operations
        forbidden = ["os.remove", "os.rmdir", "shutil.rmtree"]
        for f in forbidden:
            if f in code:
                issues.append(f"Forbidden operation: {f}")

        # Block directory traversal
        if ".." in code:
            issues.append("Directory traversal not allowed")

        # Detect file access
        matches = re.findall(r'open\(["\'](.*?)["\']', code)

        normalized_workspace = (allowed_workspace or "").replace("\\", "/").rstrip("/")

        for path in matches:
            normalized_path = path.replace("\\", "/")

            if allowed_files and normalized_path in [f.replace("\\", "/") for f in allowed_files]:
                continue
            if normalized_workspace and (
                normalized_path == normalized_workspace
                or normalized_path.startswith(normalized_workspace + "/")
            ):
                continue
            if "workspace" in normalized_path and not normalized_workspace:
                continue

            issues.append(f"Unauthorized file access: {path}")

        return len(issues) == 0, issues

    async def run(
        self,
        instruction: str,
        context: str = "",
        allowed_files=None,
        allowed_workspace: str | None = None,
    ) -> str:
        from tools.code_executor import execute_python_code, auto_install_missing
        from nexus_ai.logger import log

        t0 = time.time()
        allowed_files = allowed_files or []

        code = await self._llm(
            self.CODE_GEN_SYS,
            f"Goal: {instruction}\n\nContext:\n{context}",
        )
        code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()

        for attempt in range(1, 4):
            safe, issues = self._is_safe(code, allowed_files, allowed_workspace)

            if not safe:
                if attempt == 3:
                    return "❌ Unsafe code blocked:\n" + "\n".join(issues)
                code = await self._llm(
                    self.CODE_GEN_SYS,
                    f"Goal: {instruction}\n\nContext:\n{context}\n\n"
                    f"Safety issues:\n" + "\n".join(issues) + "\n\n"
                    f"Rewrite the code so every written file stays inside "
                    f"{allowed_workspace or './workspace/'} and keep the implementation complete.",
                )
                code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()
                continue

            auto_install_missing(code)
            result = execute_python_code(code)

            if result["success"]:
                output = result["stdout"] or "(no output)"
                log.agent(self.NAME, input_text=instruction, output_text=output,
                          duration=time.time() - t0, success=True,
                          extra={"attempts": attempt})
                return f"Code executed successfully.\n\nOutput:\n{output}"

            error = (result["error"] or result["stderr"] or "unknown").strip()

            if attempt == 3:
                log.agent(self.NAME, input_text=instruction, output_text=error,
                          duration=time.time() - t0, success=False)
                return f"Code execution failed after 3 attempts.\nLast error: {error}"

            code = await self._llm(
                self.CODE_GEN_SYS,
                f"Goal: {instruction}\n\nContext:\n{context}\n\n"
                f"Previous error:\n{error}\n\nFix the code:",
            )
            code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()

        return "Coder failed."
