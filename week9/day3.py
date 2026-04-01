from __future__ import annotations

import asyncio
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.ui import Console

from config import describe_active_model, get_model_client
from tools import (
    build_code_execution_tool,
    create_db_agent,
    create_file_agent,
    set_query_folder,
)


def _rule(char: str = "=", width: int = 78) -> str:
    return char * width


def _section(title: str, char: str = "=") -> None:
    print(f"\n{_rule(char)}")
    print(title)
    print(_rule(char))


async def build_day3_app():
    model_client = get_model_client(parallel_tool_calls=False)
    set_query_folder("mods")
    file_agent = create_file_agent(model_client)
    db_agent = create_db_agent(model_client)
    tools = [
        AgentTool(file_agent, return_value_as_last_message=True),
        AgentTool(db_agent, return_value_as_last_message=True),
    ]
    code_executor = None
    code_execution_status = "disabled"

    try:
        code_tool, code_executor = await build_code_execution_tool(model_client, query_folder="mods")
        tools.append(code_tool)
        code_execution_status = "docker + approval"
    except Exception as exc:
        code_execution_status = f"disabled ({exc})"

    orchestrator = AssistantAgent(
        name="OrchestratorAgent",
        description="Routes whole plain-English tasks to FileAgent, DatabaseAgent, and approved Docker-based code execution.",
        model_client=model_client,
        tools=tools,
        system_message=(
            "You are the day 3 orchestrator for a local AutoGen workflow.\n"
            "Available tools:\n"
            "- FileAgent for local files, CSVs, reports, text outputs, and CSV modifications (adding/dropping columns with modify_csv).\n"
            "- DatabaseAgent for SQLite inspection, read-only SQL queries, and write operations (INSERT, UPDATE, DELETE) on existing databases.\n"
            "- CodeExecutorAgent for approved Python calculations and analysis in Docker, when available. Pandas and numpy are pre-installed.\n\n"
            "Rules:\n"
            "- Use the exact tool names as provided: FileAgent, DatabaseAgent, and CodeExecutorAgent.\n"
            "- Each AgentTool accepts exactly one plain-English task string in the `task` argument. Never pass JSON objects, nested dictionaries, task schemas, or raw SQL to an AgentTool — always describe the task in plain English.\n"
            "- When delegating to DatabaseAgent, always include the exact database filename (e.g. 'in user.db') in the plain-English task string. Never omit the database name.\n"
            "- Preserve the user's full intent when delegating. If the request names an input file and an output file, include both in the same delegated task.\n"
            "- Prefer a single FileAgent call for a single CSV-to-report request instead of splitting it into separate read, analyze, and write tasks.\n"
            "- For exact file reads or writes, preserve the exact path the user requested. Do not silently substitute a different file name or location.\n"
            "- If FileAgent reports an exact requested file is missing, stop and return that error. Do not ask FileAgent to keep exploring.\n"
            "- Use FileAgent for file discovery by file name, code reading, text analysis, CSV analysis, simple SVG graph generation, and any task that must create or update a workspace file.\n"
            "- If the user asks to create or populate a SQLite database from scratch, route that task to CodeExecutorAgent because it needs to generate data.\n"
            "- If the user asks to INSERT, UPDATE, or DELETE records in an existing SQLite database with specific values or a clear SQL command, route directly to DatabaseAgent which has execute_sqlite. DatabaseAgent can handle any concrete SQL statement.\n"
            "- Only use the CodeExecutor pipeline for vague or bulk data requests where mock/random data must be generated (e.g. 'add 1000 rows', 'fill with mock data', 'populate with random entries'). For these: Step 1 — use DatabaseAgent to inspect the schema. Step 2 — use FileAgent to copy the DB into the workspace (copy_file_to_workspace with just the filename, e.g. 'user.db'). Step 3 — use CodeExecutorAgent to modify the DB at /workspace/<filename> IN PLACE (same filename, not a renamed copy), generate mock data matching the real schema, and insert it. Include the exact table names, column names, and types in the CodeExecutorAgent task. Step 4 — use FileAgent's copy_file_to_workspace with just the filename as output_path to copy the modified file back.\n"
            "- If a single task asks to create multiple generated artifacts such as a CSV, a database, and a report, first use CodeExecutorAgent to create them inside .runtime/code/mods, then continue with FileAgent to copy the requested final files into the project workspace.\n"
            "- For a mixed generation task, ask CodeExecutorAgent to create every requested runtime artifact in one run, including any requested report file.\n"
            "- When CodeExecutorAgent reports created runtime files with HOST_PATH: lines, use FileAgent's copy_file_to_workspace with the absolute project path as output_path to bring those files back.\n"
            "- Prefer copying a generated report from CodeExecutorAgent over asking FileAgent to infer report contents from a SQLite .db file.\n"
            "- For CSV modifications (adding columns, filling with mock data, transforming data): Step 1 — use FileAgent to inspect the CSV and copy it to the workspace (copy_file_to_workspace with just the filename). Step 2 — use CodeExecutorAgent to modify /workspace/<filename> IN PLACE — it must write back to the same filename, not a new one. Step 3 — use FileAgent's copy_file_to_workspace with just the filename as output_path to copy the modified file back to the project root.\n"
            "- For CSV summaries, markdown reports, or other read-only file-generation tasks, stay within FileAgent unless the user explicitly asks for Python execution.\n"
            "- For text files, word counts, or word-frequency graphs, prefer FileAgent unless the user explicitly asks for Python execution.\n"
            "- Use DatabaseAgent for all SQLite operations: schema inspection, queries, and data modifications on existing databases.\n"
            "- Use CodeExecutorAgent mainly when the user explicitly asks for Python or shell execution, or when database creation or coordinated multi-file generation is required.\n"
            "- Code execution requires explicit approval before each run.\n"
            "- Code execution writes only to .runtime/code/mods. FileAgent is the only tool that writes into the project workspace.\n"
            "- Detailed analysis is preferred over a short generic summary unless the user explicitly asks for brevity.\n"
            "- Use the fewest tool calls needed to fully solve the task.\n"
            "- If the user has not provided a path you need, ask for it clearly.\n"
            "- Do not claim that a file exists unless a writing tool reported that it wrote the file.\n"
            "- If an agent reports that requested data, columns, or tables do not exist, accept that answer. Do not re-invoke the same agent hoping for a different result.\n"
            "- Never hallucinate or fabricate data. If the database schema does not contain what the user asked for, say so clearly.\n"
            "- When the user says 'X in Y table' or 'X in the Y table', treat 'Y' as the table name and 'X' as the value to search for — do not concatenate them into a single value like 'X in Y'.\n"
            "- When a count query returns 0 unexpectedly, always follow up by fetching distinct values from that column. If a close match exists (e.g. 'PhD' when 'PhD in Education' returned 0), re-run the count with the correct value and inform the user of the match used.\n"
            "- End with a direct final answer in clean plain text."
        ),
        reflect_on_tool_use=False,
        tool_call_summary_format="{result}",
        max_tool_iterations=5,
    )

    return orchestrator, model_client, code_executor, code_execution_status


def _print_banner() -> None:
    _section("DAY 3  TOOL-CALLING AGENTS")
    print(f"Active model: {describe_active_model()}")
    print("Type a task, or 'exit' to quit.")
    print(_rule())


async def run_task(task: str) -> None:
    orchestrator, model_client, code_executor, code_execution_status = await build_day3_app()
    try:
        print(f"Code execution: {code_execution_status}")
        _section("TASK")
        print(task)
        _section("LIVE RUN", "-")
        await Console(orchestrator.run_stream(task=task), output_stats=False)
        print(_rule("-"))
    finally:
        if code_executor is not None:
            await code_executor.stop()
        await model_client.close()


async def execute_task(task: str) -> None:
    try:
        await run_task(task)
    except Exception as exc:
        _section("ERROR", "!")
        print(exc)
        print(_rule("!"))


async def interactive_cli() -> None:
    _print_banner()
    while True:
        task = input("\n[USER] ").strip()
        if task.lower() in {"exit", "quit"}:
            break
        if not task:
            continue

        _section("RUN START", "-")
        await execute_task(task)
        _section("RUN END", "-")


async def main() -> None:
    if len(sys.argv) > 1:
        await execute_task(" ".join(sys.argv[1:]))
        return
    await interactive_cli()

if __name__ == "__main__":
    asyncio.run(main())
# Translates ~/ paths to absolute paths