# File Structure

Project root: `/home/abhishekrai/week9`

This document lists the current project file layout. Runtime/cache directories are included so their locations are visible, but large generated contents like `venv/` are not expanded file-by-file.

```text
week9/
|-- .env
|-- .gitignore
|-- AGENT-FUNDAMENTALS.md
|-- FLOW-DIAGRAM.md
|-- MEMORY-SYSTEM.md
|-- TOOL-CHAIN.md
|-- dag.py
|-- day3.md
|-- day3.py
|-- day4.py
|-- filestructure.md
|-- learners_report.md
|-- main.py
|-- product.csv
|-- requirements.txt
|-- .day3_runtime/
|   `-- code/
|-- __pycache__/
|-- agents/
|   |-- __pycache__/
|   |-- answer_agent.py
|   |-- reflection_agent.py
|   |-- research_agent.py
|   |-- summarizer_agent.py
|   |-- validator.py
|   `-- worker_agent.py
|-- config/
|   |-- __init__.py
|   |-- __pycache__/
|   |-- gemini_client.py
|   |-- model_client.py
|   `-- models.yaml
|-- memory/
|   |-- __init__.py
|   |-- __pycache__/
|   |-- long_term.db
|   |-- session_memory.py
|   |-- vector_store.py
|   `-- vector_store/
|       |-- index.faiss
|       `-- meta.pkl
|-- nexus_ai/
|   |-- config.py
|   `-- main.py
|-- orchestrator/
|   |-- __pycache__/
|   `-- planner.py
|-- outputs/
|   |-- analysis_report.md
|   |-- analysis_report.txt
|   |-- analysis_report_validation.md
|   |-- simple_report_test.md
|   `-- test.md
|-- tools/
|   |-- __init__.py
|   |-- __pycache__/
|   |-- code_executor.py
|   |-- db_agent.py
|   `-- file_agent.py
`-- venv/
```

## Notes

- `agents/`, `tools/`, `memory/`, `config/`, `orchestrator/`, and `nexus_ai/` contain the main source code.
- `outputs/` contains generated reports and test markdown outputs.
- `memory/vector_store/` stores vector index artifacts.
- `.day3_runtime/`, `__pycache__/`, and `venv/` are present in the workspace but are generated/runtime-oriented directories rather than core source folders.
