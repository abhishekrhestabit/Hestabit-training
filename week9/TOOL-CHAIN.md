# TOOL-CHAIN.md — Day 3: Tool-Calling Agents

## Overview

Day 3 builds three specialist tool-using agents that operate real tools
(Python interpreter, SQLite database, file system). An Orchestrator
coordinates them to solve complex multi-tool tasks.

---

## Architecture

```
User Query
    ↓
Orchestrator  ← routes sub-tasks to specialists
    ├── File_Agent   → read_file / write_file / analyse_csv
    ├── Code_Agent   → run_python (subprocess-sandboxed)
    └── DB_Agent     → query_database / inspect_schema
         ↓
    Combined Answer (Orchestrator summarizes → TERMINATE)
```

---

## File Structure

```
day3/
├── model.yaml                  ← toggle Ollama / Gemini / Groq
├── day3_pipeline.py            ← entry point
├── config/
│   ├── __init__.py
│   └── model_loader.py         ← reads model.yaml, returns client
├── tools/
│   ├── __init__.py
│   ├── code_executor.py        ← run_python()
│   ├── db_agent.py             ← query_database(), inspect_schema()
│   └── file_agent.py           ← read_file(), write_file(), analyse_csv()
└── data/                       ← auto-created on first run
    ├── sales.csv
    └── sales.db
```

---

## Tools Reference

### `tools/code_executor.py`
| Function | Description |
|---|---|
| `run_python(code)` | Execute Python string in subprocess, return stdout/stderr |
| `execute_python_code(code, timeout)` | Low-level, returns dict with success/stdout/stderr |

### `tools/db_agent.py`
| Function | Description |
|---|---|
| `query_database(sql, db_path?)` | Run SQL, return formatted results |
| `inspect_schema(db_path?)` | Show all tables and columns |
| `insert_rows(table, rows, db_path?)` | Bulk insert list of dicts |
| `create_sample_sales_db(db_path?)` | Create demo DB for testing |

### `tools/file_agent.py`
| Function | Description |
|---|---|
| `read_file(file_path)` | Auto-detect and read .txt/.csv/.json |
| `write_file(file_path, content, append?)` | Write or append text |
| `analyse_csv(file_path)` | Stats summary (no pandas needed) |
| `create_sample_csv(file_path?)` | Create demo CSV for testing |

---

## Switching Models

Edit `model.yaml` → change `active_provider`:

```yaml
active_provider: "ollama"    # local Qwen via Ollama (CPU)
# active_provider: "gemini"  # Google Gemini API
# active_provider: "groq"    # Groq cloud API (fast, free tier)
```

Then add your API key under the relevant section.

---

## How to Run

```bash
# Make sure Ollama is running (for local mode)
ollama serve
ollama pull qwen2.5

# Run Day 3
python day3_pipeline.py
```

---

## Reuse in Later Days

| Component | Day 4 | Day 5 (NEXUS AI) |
|---|---|---|
| `tools/code_executor.py` | ✅ memory-aware code agent | ✅ Coder Agent |
| `tools/db_agent.py` | ✅ long-term memory storage | ✅ Analyst Agent |
| `tools/file_agent.py` | ✅ episodic log reading | ✅ Analyst + Reporter |
| `config/model_loader.py` | ✅ same config | ✅ same config |

---

## Example Task Output

```
Task: "Analyze data/sales.csv... top 3 products... SQL by region... report"

Orchestrator → File_Agent: read + analyse CSV
File_Agent   → runs analyse_csv() → stats output

Orchestrator → Code_Agent: top 3 products by revenue
Code_Agent   → writes + runs Python → top3 list

Orchestrator → DB_Agent: total sales per region
DB_Agent     → inspect_schema → query_database → table

Orchestrator → summarizes all → TERMINATE
```