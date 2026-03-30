# Day 3 — Tool-Calling Agents

## Architecture

Day 3 uses a fully AutoGen-based tool chain:

- `OrchestratorAgent` is an `AssistantAgent` that plans the task and delegates work.
- `FileAgent` is an `AssistantAgent` with file tools for discovery, reading, CSV inspection, and writing.
- `DatabaseAgent` is an `AssistantAgent` with read-only SQLite tools.
- `CodeAgent` is an `AssistantAgent` backed by `PythonCodeExecutionTool` and `LocalCommandLineCodeExecutor`.

The orchestrator calls the specialist agents through `AgentTool`, which keeps the orchestration inside AutoGen instead of hand-written routing logic.

## CLI Design

The CLI lives in `day3.py`.

- `python day3.py`
  Starts an interactive testing loop.
- `python day3.py "Analyze /path/to/file.csv and give 5 insights"`
  Runs one task and exits.

The terminal output is streamed through AutoGen `Console(...)` so you can see:

- the user task
- when the orchestrator delegates to a specialist
- the specialist result
- the final answer

Each run is wrapped with `RUN START` / `RUN END` separators so repeated testing stays readable.

## Tool Coverage

### FileAgent

- list files
- read text files
- inspect CSV structure and sample rows
- write text files inside the project workspace

### DatabaseAgent

- list SQLite tables
- inspect table schema
- run read-only SQL queries

### CodeAgent

- execute short Python snippets for calculations and deeper analysis
- runs code in `.day3_runtime/code`
- uses the project virtual environment when available

## Notes

- The orchestrator disables parallel tool calls because `AgentTool` runs stateful agents.
- The SQLite tools are read-only by design.
- The code executor uses the local machine, which is convenient for development and testing but should be treated carefully.
