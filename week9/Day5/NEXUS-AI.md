# Day 5 — NEXUS AI: Multi-Agent Orchestration System

## Overview

NEXUS AI is a full-featured multi-agent orchestration system that takes a user query, generates a structured execution plan, dispatches specialized worker agents in a graph-based workflow, subjects results to a critic/optimizer/validator review loop, and produces a final report. Built on Microsoft AutoGen's `GraphFlow` with persistent memory from Day 4.

## Architecture

```
User Query
    │
    ▼
┌──────────────────┐
│     Planner       │  → Generates a structured ExecutionPlan (JSON)
│  (+ memory tools) │     task_kind, steps, worker assignments, deliverables
└──────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│                    GraphFlow (DAG)                     │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Worker 1  │→│ Worker 2  │→│ Worker N  │  (chain)  │
│  │researcher │  │ analyst  │  │  coder   │           │
│  └──────────┘  └──────────┘  └──────────┘           │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐     ┌────────────┐                     │
│  │  Critic   │◄──►│ Optimizer   │  (fix loop)        │
│  │ [APPROVED]│     │             │                     │
│  └──────────┘     └────────────┘                     │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ Validator │  → [VALIDATED] or [NOT_VALIDATED]      │
│  └──────────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ Reporter  │  → Final user-facing summary           │
│  │(+ memory) │     + saves task summary to long-term  │
│  └──────────┘                                        │
└──────────────────────────────────────────────────────┘
    │
    ▼
 Final Report (printed to CLI)
```

## Agent Roles & Tool Access

| Agent | Role | Tools |
|---|---|---|
| **Planner** | Break query into steps, assign workers | Memory tools (save/retrieve facts) |
| **Researcher** | Read files, search web, gather info | `list_files`, `read_text_file`, `inspect_csv`, `web_search` |
| **Analyst** | Analyze data, write reports | `analyze_csv`, `inspect_csv`, `query_sqlite`, `write_text_file`, `get_source_info` |
| **Coder** | Execute code, build projects | `CodeExecutorAgent` (Docker), `write_text_file`, `copy_file_to_workspace` |
| **Critic** | Judge work quality | None (reasoning only) |
| **Optimizer** | Fix issues the Critic identified | `list_files`, `read_text_file`, `write_text_file`, `get_source_info`, `query_sqlite` |
| **Validator** | Verify user intent is satisfied | None (reasoning only) |
| **Reporter** | Present final result, save to memory | Memory tools (save/retrieve facts) |

**Key constraint:** Only analyst and coder can write files. Researcher is read-only. The Planner's routing rules enforce this.

## Execution Plan Schema

The Planner outputs a structured JSON plan validated against Pydantic models:

```
ExecutionPlan
├── plan_summary      (what we're doing)
├── task_kind         (simple_answer | artifact | mixed | fact_storage)
├── finish_condition  (how to know we're done)
├── query_folder      (output routing: .runtime/code/<folder>/)
└── steps[]
    ├── step_id
    ├── title
    ├── worker        (researcher | analyst | coder)
    ├── instructions
    ├── success_criteria
    ├── deliverables  (plain filenames — routing is automatic)
    └── depends_on
```

## Planner Routing Rules

| User Intent | Plan |
|---|---|
| State a personal fact | `task_kind: fact_storage`, no steps |
| Read/explain a file | Researcher (1 step) |
| Read file + produce report | Researcher → Analyst (2 steps) |
| CSV analysis | Analyst (1 step) |
| Web research | Researcher (1 step) |
| Web research + report file | Researcher → Analyst (2 steps) |
| Create SQLite DB from CSV | Coder → Analyst (2 steps) |
| Generate code/scripts | Coder (1 step) |
| Full project architecture | Coder (1 step, all files in deliverables) |

Max 3 steps per plan. Up to 2 replanning cycles if the graph fails.

## Memory Integration

Inherits the full Day 4 memory system:

- **Session Memory** — Rolling 20-message window (volatile)
- **Vector Store** — FAISS semantic search (persistent)
- **Long-Term Store** — SQLite with categories (persistent)

Memory tools available to Planner and Reporter:
- `save_core_fact(fact, category)` — save with categorization
- `get_facts_by_date(YYYY-MM-DD)` — temporal retrieval
- `get_facts_by_category(category)` — topic-based retrieval

Critic, Validator, and Reporter also receive auto-injected memory context on every turn.

## Runtime Settings

| Setting | Default | Purpose |
|---|---|---|
| `max_plan_cycles` | 2 | Outer replan loop limit |
| `max_graph_turns` | 25 | Safety limit per GraphFlow run |
| `max_tool_iterations` | 4 | Per-agent tool call rounds |

## CLI Commands

| Command | Action |
|---|---|
| `stats` | Print memory state |
| `clear` | Wipe all memory (session + vector + SQLite) |
| `exit` | Quit and print final stats |

## File Structure

```
Day5/
├── nexus_ai/
│   ├── __init__.py
│   ├── main.py                    ← Entry point, orchestration loop, graph builder
│   ├── config.py                  ← Agent prompts, runtime settings
│   └── schemas.py                 ← Pydantic models (ExecutionPlan, PlanStep)
├── memory/
│   ├── __init__.py
│   ├── session_memory.py          ← SessionMemory, FactMemory, MemorySystem
│   ├── vector_store.py            ← VectorStore (FAISS), LongTermStore (SQLite)
│   ├── long_term.db
│   └── vector_store/
│       ├── index.faiss
│       └── meta.pkl
├── tools/
│   ├── __init__.py
│   ├── file_agent.py              ← File I/O, CSV analysis, source inspection
│   ├── db_agent.py                ← SQLite operations
│   ├── code_executor.py           ← Docker-based code execution
│   └── search_tool.py             ← DuckDuckGo web search
├── config/
│   ├── __init__.py
│   ├── model_client.py
│   ├── gemini_client.py
│   └── models.yaml
├── logs/
│   └── nexus_trace.log
├── .runtime/code/                 ← Auto-routed output per query folder
└── NEXUS-AI.md
```

## Usage

```bash
python Day5/nexus_ai/main.py
# Interactive loop — full Plan → Execute → Critique → Validate → Report pipeline
```
