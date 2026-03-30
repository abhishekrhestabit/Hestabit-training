from __future__ import annotations

import os
from pathlib import Path

from autogen_agentchat.agents import ApprovalRequest, ApprovalResponse, CodeExecutorAgent
from autogen_agentchat.tools import AgentTool
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = PROJECT_ROOT / ".runtime" / "code"
CONTAINER_RUNTIME_DIR = "/workspace"


def _approval_func(request: ApprovalRequest) -> ApprovalResponse:
    auto_approve = os.getenv("DAY3_AUTO_APPROVE_CODE_EXECUTION", "").strip().lower()
    if auto_approve in {"1", "true", "yes"}:
        return ApprovalResponse(approved=True, reason="Approved via DAY3_AUTO_APPROVE_CODE_EXECUTION")

    print("\n" + "=" * 78)
    print("CODE EXECUTION APPROVAL")
    print("=" * 78)
    print(request.code)
    print("=" * 78)

    while True:
        try:
            user_input = input("Run this code in Docker? [y/N]: ").strip().lower()
        except EOFError:
            return ApprovalResponse(approved=False, reason="Approval denied because no interactive input was available")

        if user_input in {"y", "yes"}:
            return ApprovalResponse(approved=True, reason="Approved by user")
        if user_input in {"", "n", "no"}:
            return ApprovalResponse(approved=False, reason="Denied by user")

        print("Please enter 'y' or 'n'.")


async def build_code_execution_tool(model_client, query_folder: str | None = None) -> tuple[AgentTool, DockerCommandLineCodeExecutor]:
    work_dir = RUNTIME_DIR / query_folder if query_folder else RUNTIME_DIR
    work_dir.mkdir(parents=True, exist_ok=True)

    executor = DockerCommandLineCodeExecutor(
        image="python:3-slim",
        timeout=90,
        work_dir=work_dir,
        bind_dir=work_dir,
        extra_volumes={
            str(PROJECT_ROOT.resolve()): {
                "bind": str(PROJECT_ROOT.resolve()),
                "mode": "ro",
            }
        },
        delete_tmp_files=True,
    )
    await executor.start()

    agent = CodeExecutorAgent(
        "CodeExecutorAgent",
        code_executor=executor,
        model_client=model_client,
        max_retries_on_error=2,  # auto-retry failed code (e.g. missing module → rewrite with stdlib)
        description="Execute Python or shell code in Docker. Use for DB creation, data processing, multi-artifact tasks.",
        system_message=(
            "One ```python``` or ```sh``` code block per task. Stdlib only (csv, sqlite3, json, os, math). NO pandas/numpy.\n"
            f"Read-only project: {PROJECT_ROOT.resolve()}. Writable dir: {CONTAINER_RUNTIME_DIR} (host: {work_dir.resolve()}).\n"
            f"IMPORTANT: Write ALL files directly to {CONTAINER_RUNTIME_DIR}/<filename>. Do NOT create subdirectories.\n"
            "Do only the immediate task. Inspect real files before assuming schema. No destructive commands (rm, mv, sudo, curl, wget).\n"
            "CSV-to-SQLite: one script, use real headers, infer types (REAL/INTEGER not TEXT), drop+recreate if rerunning.\n"
            f"Print created files as: HOST_PATH: {work_dir.resolve()}/<filename>\n"
            "Final response: short summary + HOST_PATH lines. On failure: start with 'ERROR:' and describe the real issue."
        ),
        supported_languages=["python", "sh", "bash", "shell"],
        approval_func=_approval_func,
    )
    return AgentTool(agent, return_value_as_last_message=True), executor
