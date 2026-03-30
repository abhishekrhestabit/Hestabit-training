# Day 3 Report

## Overview

Day 3 implements a full AutoGen-based local tool-calling workflow. The goal of this stage was to move beyond the earlier fixed multi-agent chat patterns and build a practical agent that can inspect files, analyze CSV data, query SQLite databases, and execute approved Python code when tool-based analysis alone is not enough.

The current implementation uses a single `AssistantAgent` as the orchestrator, but it now delegates work to three specialist agents through `AgentTool`:

- `FileAgent`
- `DatabaseAgent`
- `CodeExecutorAgent`

This keeps the launchpad-style specialist structure while still making the system easy to test from one CLI entrypoint.

## What Day 3 Delivers

- A CLI entrypoint in `day3.py`
- A tool-calling AutoGen orchestrator
- A `FileAgent` for file, CSV, and report tasks
- A `DatabaseAgent` for SQLite analysis
- A `CodeExecutorAgent` for approved Docker-based Python execution
- Shared model loading through `.env` and `config/models.yaml`
- Readable terminal output for manual testing

## Main Architecture

Day 3 is centered around the `Day3App` dataclass in `day3.py`. It contains:

- `model_client`: the active AutoGen chat-completion client
- `orchestrator`: the main `AssistantAgent`
- `code_executor`: the Docker-backed executor when available
- `code_execution_status`: a short human-readable runtime status string

The application is assembled in `build_day3_app()`. That function:

1. Loads the active model client using the shared config layer.
2. Creates `FileAgent` and `DatabaseAgent`.
3. Wraps those agents with `AgentTool`.
4. Tries to add the Docker-backed `CodeExecutorAgent`.
5. Builds the `OrchestratorAgent` with a system message that guides routing.
6. Returns a fully initialized `Day3App`.

## Why This Design Was Chosen

Instead of using a group-chat team for Day 3, the implementation uses one orchestrator with specialist agents exposed as tools. This is a better fit for the current objective because Day 3 is mainly about accurate routing, local analysis, and controlled execution.

This structure keeps the flow:

- minimal
- easier to debug
- easier to test from the CLI
- more predictable than free-form agent-to-agent conversation

It also aligns well with AutoGen’s agent-as-tool model, where a top-level `AssistantAgent` can route tasks to specialist agents while those specialists use their own internal function tools.

## Workflow

## Startup Flow

When `python day3.py` runs:

1. The CLI banner is printed.
2. The active provider and model are shown using `describe_active_model()`.
3. The user enters a task.
4. `execute_task()` wraps the request in basic error handling.
5. `run_task()` creates a fresh `Day3App`, prints runtime sections, and streams the agent run through `Console`.

If code execution is available, the CLI shows:

`Code execution: docker + approval`

If Docker is unavailable or startup fails, the app still runs with the rest of the tools and simply disables code execution.

## Task Execution Flow

For each task:

1. The orchestrator receives the user prompt.
2. It decides which specialist agent is most appropriate.
3. Tool calls and tool results are streamed live in the terminal.
4. The agent reflects on tool output and produces the final answer.
5. The app closes resources cleanly after the run.

The run is intentionally shown in readable sections:

- `RUN START`
- `TASK`
- `LIVE RUN`
- `RUN END`

This makes repeated manual testing much easier.

## FileAgent

File and CSV handling lives in `tools/file_agent.py`. The orchestrator does not call the file functions directly anymore. Instead, it calls `FileAgent`, and `FileAgent` decides which internal file tool to use.

### `list_files`

Used to discover local files quickly. It supports:

- a directory
- a glob pattern
- a result limit

It also skips low-value directories such as:

- `.git`
- `.day3_runtime`
- `__pycache__`
- `venv`

### `read_text_file`

Reads a text file and returns:

- the resolved path
- a trimmed content preview

This is mainly used when the user asks to inspect code, markdown, or other local text files.

### `inspect_csv`

Returns a quick CSV preview with:

- row count
- column list
- dtypes
- sample rows

This is useful when the user wants structure and context before deeper analysis.

### `analyze_csv`

Returns a compact profile of the dataset, including:

- row and column count
- missing values
- numeric summaries
- top categorical counts

This function was intentionally simplified to be generic. Earlier versions had assumptions tied to specific columns like `Price` and `Category`, but the current version works across a wider range of CSVs.

### `write_text_file`

Writes final content inside the project workspace only. This is used for normal file generation tasks such as creating notes or reports.

### `write_analysis_report`

This is the specialized report-writing tool for source analysis. It:

- checks that the output path stays inside the project
- checks that the source file exists
- ensures the report is not empty
- reads the source file
- prepends a generated `Source Snapshot`

The `Source Snapshot` includes:

- source path
- approximate line count
- class names
- function names

This keeps analysis files more grounded without forcing a rigid report schema.

## DatabaseAgent

SQLite support lives in `tools/db_agent.py`. The orchestrator now calls `DatabaseAgent`, and that agent uses its internal tools:

- `list_sqlite_tables`
- `describe_sqlite_table`
- `query_sqlite`

### Safety Model for SQL

The database layer is intentionally read-only.

Important protections:

- the connection uses SQLite read-only mode
- only `SELECT`, `WITH`, `PRAGMA`, and `EXPLAIN` queries are allowed
- write queries such as `INSERT`, `UPDATE`, and `DELETE` are rejected

This means the agent can inspect and analyze a database, but it cannot mutate it.

## Code Execution

Approved Python execution is implemented in `tools/code_executor.py`.

This part uses AutoGen’s `CodeExecutorAgent` together with `DockerCommandLineCodeExecutor`, and the orchestrator calls it the same way it calls the other specialist agents.

### How It Works

1. The runtime directory `.day3_runtime/code` is created.
2. A Docker executor is started.
3. The project root is mounted read-only.
4. The runtime working directory is mounted writable for execution artifacts.
5. The orchestrator gets an `AgentTool` wrapper around the code executor.

### Approval Flow

Before Python code runs, the approval function asks the user for confirmation unless:

`DAY3_AUTO_APPROVE_CODE_EXECUTION=true`

is set in the environment.

This keeps the system practical for testing while still protecting the machine during normal interactive use.

### Execution Guardrails

Current execution behavior is intentionally constrained:

- Docker-based execution
- Python-only
- no shell scripts
- project mount is read-only
- intended for analysis, calculations, and summaries

This is a much safer setup than directly running generated code in the repository or local shell.

## Model and Provider Flow

Day 3 uses the shared configuration system so it can work with multiple providers without changing application code.

The model-loading flow is:

1. `.env` is loaded through `config/model_client.py`
2. provider metadata is read from `config/models.yaml`
3. the active provider is selected using `MODEL_PROVIDER`
4. the correct AutoGen client is built

Currently the configured providers are:

- Gemini
- Groq
- Ollama

### Gemini Support

Gemini is handled separately through `config/gemini_client.py`. That file exists because Gemini tool-calling needed a dedicated compatibility layer through Semantic Kernel, including message and thought-signature handling.

### Shared Client Benefit

This keeps Day 3 consistent with Day 1 and Day 2:

- same provider registry
- same `.env` pattern
- same model-loading entrypoint

## AutoGen Practices Used

Day 3 follows a few solid AutoGen patterns:

- simple Python functions exposed as internal specialist-agent tools using annotations and docstrings
- one `AssistantAgent` coordinating specialist agents through `AgentTool`
- `reflect_on_tool_use=True` so raw tool output becomes a cleaner final answer
- `parallel_tool_calls=False` in the shared model client for safer agent-as-tool behavior
- `Console(run_stream(...))` for readable streamed testing
- `CodeExecutorAgent` with Docker for safer execution

This keeps the implementation aligned with AutoGen’s agent-tool delegation pattern without turning Day 3 into a full free-form group-chat workflow.

## How the CLI Runs

The CLI supports two modes.

### Interactive Mode

```bash
python day3.py
```

This opens the banner and waits for tasks:

```text
[USER] Analyze product.csv and give me top 5 insights
```

### Single-Shot Mode

```bash
python day3.py "Read day3.py and create a report in outputs/day3_report.md"
```

This is useful for quick testing and automation.

## Typical Task Types Day 3 Can Handle

- inspect a local file
- read and summarize markdown or Python files
- analyze a CSV dataset
- inspect a SQLite schema
- run a read-only SQLite query
- generate a report file
- use Docker-based Python for calculations when needed

## Current Strengths

- clear CLI output for testing
- shared provider configuration
- launchpad-style specialist-agent structure
- safe local file writing
- generic CSV analysis
- read-only database handling
- safer code execution through Docker and approval
- minimal but practical AutoGen architecture

## Current Limitations

- code execution depends on Docker being available locally
- text-file reads are preview-based, so extremely large files may still need more targeted reads
- output quality still depends on the selected model and provider behavior

## Summary

Day 3 is the transition point where the project becomes a practical local AutoGen system instead of a fixed conversational demo. It now has:

- a shared model-config layer
- a real tool-calling orchestrator
- specialist file, database, and code-execution agents
- file, CSV, and SQLite support
- report generation
- Docker-based approved Python execution
- a readable CLI for testing

In short, Day 3 establishes the working foundation for more advanced autonomous behavior in later days while keeping the implementation small, testable, and safe enough for local development.
