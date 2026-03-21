
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

from autogen_core.models import UserMessage, SystemMessage

from config.model_loader import get_model_client
from tools.code_executor import execute_python_code, auto_install_missing
from tools.db_agent      import query_database, inspect_schema
from tools.file_agent    import read_txt, read_csv, read_json, write_txt, write_csv, read_file


# ─────────────────────────────────────────────────────────────────
#  Colour helpers for CLI progress display
# ─────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    GREY   = "\033[90m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"

def hdr(text):   print(f"\n{C.BOLD}{C.CYAN}{'─'*60}{C.RESET}\n{C.BOLD}{C.CYAN}  {text}{C.RESET}\n{'─'*60}")
def ok(text):    print(f"  {C.GREEN}✅ {text}{C.RESET}")
def warn(text):  print(f"  {C.YELLOW}⚠️  {text}{C.RESET}")
def err(text):   print(f"  {C.RED}❌ {text}{C.RESET}")
def info(text):  print(f"  {C.GREY}{text}{C.RESET}")
def step(n, t):  print(f"\n{C.BOLD}{C.BLUE}  [{n}] {t}{C.RESET}")
def fixing(t):   print(f"  {C.MAGENTA}🔧 {t}{C.RESET}")


# ─────────────────────────────────────────────────────────────────
#  LLM call helper — plain request/response, no agents
# ─────────────────────────────────────────────────────────────────

async def llm(model_client, system: str, user: str) -> str:
    """Single focused LLM call. Returns the text response."""
    response = await model_client.create(
        messages=[
            SystemMessage(content=system),
            UserMessage(content=user, source="pipeline"),
        ]
    )
    content = response.content
    if isinstance(content, list):
        content = " ".join(
            p.text if hasattr(p, "text") else str(p) for p in content
        )
    return (content or "").strip()


# ─────────────────────────────────────────────────────────────────
#  STEP 1 — PLANNER
#
#  Two-phase approach (Cursor/Copilot style):
#    Phase A — THINK: reason about what the query actually needs
#    Phase B — PLAN:  produce the minimal task list from that reasoning
#
#  Phase A prevents the model from jumping straight to "read a file"
#  when no file exists, or adding unnecessary tasks.
# ─────────────────────────────────────────────────────────────────

THINKER_SYSTEM = """\
You are an expert at understanding what a user request truly requires.

Analyse the user's request and answer these questions concisely:

1. DATA SOURCE — where does the data come from?
   - An existing file on disk (user mentioned a path like data/x.csv)?
   - A database the user mentioned (data/x.db)?
   - General knowledge you already have (facts, lists, tables)?
   - Data that needs to be computed/generated?

2. OUTPUT — what does the user want as the final result?
   - A file saved to disk? (which path, which format?)
   - A printed answer / summary?
   - Both?

3. STEPS NEEDED — what is the minimal sequence of operations?
   List only what is strictly necessary.
   Do NOT add reading steps if the data must be generated from knowledge.
   Do NOT add database steps if no database was mentioned.

Be concise. No JSON yet — just plain reasoning.\
"""

PLANNER_SYSTEM = """\
You are a task planner. Convert the reasoning provided into a minimal JSON task list.

AVAILABLE TASK TYPES:
  read_txt    — read any text-based file: .txt, .md, .py, .yaml, .log, .html, etc.
  read_csv    — read an existing .csv file from disk into structured data
  read_json   — read an existing .json file from disk
  write_txt   — write/create any text file: .txt, .md, .py, .yaml, .html, etc.
  write_csv   — write structured rows to a .csv file (format guaranteed safe)
  run_code    — execute Python code for calculations or data processing
  run_shell   — run a shell command (pip install, mkdir, etc.)
  query_db    — query an existing SQLite .db file with SQL

OUTPUT FORMAT — raw JSON array only, no fences, no explanation:
  [{"id": 1, "type": "...", "description": "...", "args": {...}}, ...]

ARGS PER TYPE:
  read_txt:   {"file_path": "path/to/file"}        (.txt, .md, .py, .yaml, .log, .html)
  read_csv:   {"file_path": "path/to/file.csv"}
  read_json:  {"file_path": "path/to/file.json"}
  write_txt:  {"file_path": "path/to/file", "text": "GENERATE"}
              ALWAYS use "GENERATE" — never write the text inline in the plan.
              The content generator will write a properly formatted document.
              Handles: .txt, .md (markdown), .py (Python), .yaml, .html, etc.
  write_csv:  {"file_path": "path/to/file.csv", "rows": "GENERATE"}
              If you already know the data, inline it as a list of dicts:
              {"file_path": "path/to/file.csv", "rows": [{"name":"Jupiter","diameter_km":139820,"moons":95}, ...]}
              IMPORTANT: rows must be a list of DICTS ({"col": val}), NOT a list of lists ([val, val]).
  run_shell:  {"command": "exact shell command string"}
  run_code:   {"goal": "specific description of what the code must compute or print"}
              goal is REQUIRED and must be specific — the code generator writes code from it.
              BAD:  {"goal": "analyze file"}  ← too vague, will generate broken code
              GOOD: {"goal": "Use Python ast module to parse dag.py from the context above,
                     extract all function names, their arguments, and import statements,
                     then print each as a labelled summary"}
  query_db:   {"db_path": "path/to/file.db", "goal": "what to query in plain English"}

CRITICAL RULES — read these before producing the plan:

  RULE 1 — DO NOT invent files.
    Only use read_txt / read_csv / read_json / query_db if the user
    explicitly mentioned that file or database path.
    If no file was mentioned, the data must come from knowledge or generation.

  RULE 2 — Use write_csv for tabular data you already know.
    If the user asks to "create a CSV of the 5 largest planets",
    you already know this data — just write_csv with rows=GENERATE.
    Do NOT add a read step for a file that does not exist.

  RULE 3 — Minimum tasks.
    Ask: can this be done in one task? If yes, use one task.
    "Create planets.csv"              → [write_csv]             (1 task)
    "Read sales.csv"                  → [read_csv]              (1 task)
    "Read sales.csv, find top 3"      → [read_csv, run_code]    (2 tasks)
    "Write a report to file.txt"      → [write_txt]             (1 task)
    "Write a report to file.md"       → [write_txt]             (1 task, same tool)
    "Create a Python script file.py"  → [write_txt]             (1 task, same tool)
    "Read script.py and explain it"   → [read_txt]              (1 task)
    "Read config.yaml"                → [read_txt]              (1 task)

  RULE 4 — run_code only when computation is needed.
    Do not add run_code just because data was read.
    Only add it if the user explicitly wants analysis, ranking, calculation.

  RULE 5 — query_db only if a .db file was mentioned by the user.

Output raw JSON array only. No ```json. No explanation.\
"""


async def plan(model_client, query: str) -> list[dict]:
    hdr("PLANNER — analysing request")

    # Phase A — Think: understand what the query truly needs
    thinking = await llm(model_client, THINKER_SYSTEM,
                         f"User request: {query}")
    info(f"Reasoning:\n{thinking}\n")

    # Phase B — Plan: convert reasoning into task list
    plan_prompt = (
        f"User request: {query}\n\n"
        f"Reasoning about what is needed:\n{thinking}\n\n"
        f"Now produce the minimal JSON task list."
    )
    raw = await llm(model_client, PLANNER_SYSTEM, plan_prompt)
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    info(f"Raw plan:\n{raw}")

    # Parse JSON — try full parse, then array extraction, then safe fallback
    tasks = None
    try:
        parsed = json.loads(raw)
        tasks = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            try:
                tasks = json.loads(match.group())
            except Exception:
                pass

    if not tasks:
        warn("Could not parse plan — using safe single-task fallback")
        # Derive a sensible fallback from the query itself
        q = query.lower()
        if any(w in q for w in ["create", "generate", "make", "write"]) and ".csv" in q:
            # Extract file path if mentioned
            m = re.search(r'[\w./]+\.csv', query)
            fp = m.group() if m else "data/output.csv"
            tasks = [{"id": 1, "type": "write_csv",
                      "description": query, "args": {"file_path": fp, "rows": "GENERATE"}}]
        elif ".csv" in q:
            m = re.search(r'[\w./]+\.csv', query)
            fp = m.group() if m else "data/output.csv"
            tasks = [{"id": 1, "type": "read_csv",
                      "description": query, "args": {"file_path": fp}}]
        else:
            tasks = [{"id": 1, "type": "write_txt",
                      "description": query,
                      "args": {"file_path": "data/answer.txt", "text": "GENERATE"}}]

    print()
    for t in tasks:
        print(f"  {C.BOLD}Task {t['id']}{C.RESET}: [{t['type']}] {t['description']}")
    return tasks


# ─────────────────────────────────────────────────────────────────
#  STEP 2 — CODE GENERATOR
#  Called when a run_code task needs actual code written.
# ─────────────────────────────────────────────────────────────────

CODE_GEN_SYSTEM = """\
You are a Python code writer. Write complete, runnable Python code to
accomplish the given goal.

RULES:
  - Use print() for every output — that is the only thing captured.
  - You may use any library (pandas, csv, statistics, etc.).
    Missing packages will be auto-installed before execution.
  - Output ONLY the raw Python code. No explanation. No markdown fences.
  - Do not include ```python or ```. Just raw code.\
"""

async def generate_code(model_client, goal: str, context: str) -> str:
    prompt = f"Goal: {goal}\n\nContext from previous tasks:\n{context}"
    code = await llm(model_client, CODE_GEN_SYSTEM, prompt)
    # Strip fences if model added them
    code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()
    return code


# ─────────────────────────────────────────────────────────────────
#  STEP 2b — SQL GENERATOR
# ─────────────────────────────────────────────────────────────────

SQL_GEN_SYSTEM = """\
You are a SQLite expert. Write a single, correct SQL query.

You will be given:
  1. The database schema — table names, exact column names, types, sample rows
  2. The goal — what the query should compute

STRICT RULES:
  - Use ONLY column names that appear in the schema. Never guess or invent columns.
  - Read the sample rows to understand what values are stored in each column.
  - For aggregations (total, sum, average): use the exact numeric column name from schema.
  - Output ONLY the raw SQL query. No explanation. No markdown. No semicolon at end.

EXAMPLE:
  Schema shows: Table sales — columns: product TEXT, region TEXT, amount REAL, units INTEGER
  Goal: total sales per region
  Correct SQL: SELECT region, SUM(amount) as total_sales FROM sales GROUP BY region ORDER BY total_sales DESC\
"""

async def generate_sql(model_client, goal: str, schema: str) -> str:
    prompt = (
        f"Schema:\n{schema}\n\n"
        f"Goal: {goal}\n\n"
        f"Write the SQL query using ONLY the exact column names shown in the schema above:"
    )
    sql = await llm(model_client, SQL_GEN_SYSTEM, prompt)
    sql = re.sub(r"```(?:sql)?", "", sql).strip().rstrip("`").strip()
    # Strip trailing semicolon if present
    sql = sql.rstrip(";").strip()
    return sql


# ─────────────────────────────────────────────────────────────────
#  STEP 2c — FILE CONTENT GENERATOR
#  Produces well-formatted documents — reports, READMEs, summaries.
#  Detects the output format from the file extension and description.
# ─────────────────────────────────────────────────────────────────

CONTENT_GEN_SYSTEM = """\
You are a professional technical writer and Python developer.
Your job is to write high-quality file content.

DETECT THE FILE TYPE from the file path and description, then follow the right rules:

── FOR .py FILES (Python scripts) ────────────────────────────────
  - Write clean, complete, runnable Python code
  - Include a docstring at the top explaining what the script does
  - Add inline comments for clarity
  - Use proper Python conventions (type hints if appropriate)
  - Output raw Python code only — no markdown fences

── FOR .md FILES (Markdown documents) ────────────────────────────
  - Use full Markdown formatting: # Title, ## Sections, **bold**, lists
  - Structure: Introduction → Body sections → Conclusion
  - Be thorough and informative
  - Output raw Markdown only — no fences around the whole document

── FOR .txt/.log FILES (Plain text) ──────────────────────────────
  - Use Markdown-style formatting (still readable as plain text)
  - Clear headings with === or --- underlines, or ## prefix
  - Bullet points with - or *
  - Be thorough — minimum 300 words with real structure

── FOR .yaml/.yml FILES ──────────────────────────────────────────
  - Write valid YAML syntax
  - Add comments explaining each section

── FOR .html FILES ───────────────────────────────────────────────
  - Write valid HTML5 with proper structure
  - Include basic inline CSS if helpful

UNIVERSAL RULES:
  - Start directly with the content — no "Here is the file:" preamble
  - No wrapping code fences around the entire output
  - Make it genuinely useful, not a placeholder\
"""

async def generate_file_content(model_client, description: str, context: str) -> str:
    """Generate well-formatted file content based on file type and description."""
    prompt = (
        f"Write the following file:\n{description}\n\n"
        f"Context from previous tasks (use this data if relevant):\n{context}"
    )
    content = await llm(model_client, CONTENT_GEN_SYSTEM, prompt)
    # Strip any wrapping fences the model added despite instructions
    content = re.sub(r"^```[\w]*\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n?```\s*$", "", content, flags=re.MULTILINE)
    return content.strip()


CSV_ROWS_SYSTEM = """\
You are a data generator. Generate rows for a CSV file as a JSON array of objects.

RULES:
  - Output ONLY a raw JSON array of objects. No explanation. No markdown fences.
  - Every object must have the same keys (column names).
  - Values must be plain strings or numbers — no nested objects.
  - Example: [{"name":"Earth","diameter_km":12742,"moons":1}, ...]
  - Output raw JSON only. No ```json fences.\
"""

async def generate_csv_rows(model_client, description: str, context: str) -> list[dict] | None:
    """
    Ask the LLM to generate structured CSV rows as a JSON array of dicts.
    Returns list[dict] on success, None on failure.
    Using JSON array guarantees write_csv() gets structured data, not a string.
    """
    prompt = f"Generate CSV rows for: {description}\n\nContext:\n{context}"
    raw = await llm(model_client, CSV_ROWS_SYSTEM, prompt)
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        rows = json.loads(raw)
        if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], dict):
            return rows
    except Exception:
        # Try extracting just the array portion
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


# ─────────────────────────────────────────────────────────────────
#  STEP 3 — EXECUTOR
#  Runs each task, returns result string.
#  If it fails, calls fixer once.
# ─────────────────────────────────────────────────────────────────

FIX_SYSTEM = """\
You are a debugging assistant. A Python code execution failed. Your job is to
provide a corrected version of the code.

Output a JSON object with EXACTLY these fields:
{
  "diagnosis": "one sentence explaining the root cause",
  "fix_type": "rewrite_code",
  "fixed_code": "...complete corrected Python code here..."
}

If the error is ModuleNotFoundError, set fix_type to "run_shell_then_retry" and add:
  "shell_command": "pip install <package_name>"

RULES:
  - fixed_code must be complete, runnable Python — not a snippet
  - fixed_code must use print() for all output
  - Output raw JSON only. No markdown fences around the JSON.
  - The fixed_code value must be a valid JSON string (escape newlines as \\n)\
"""

async def fix_task(model_client, task: dict, error: str, code: str = "") -> dict:
    """
    Ask LLM to diagnose failure and return a fix.
    Robustly extracts fixed_code even from partially malformed responses.
    """
    prompt = (
        f"Task goal: {task.get('description', '')}\n\n"
        f"Error:\n{error}\n\n"
        f"Code that failed:\n{code}"
    )
    raw = await llm(model_client, FIX_SYSTEM, prompt)

    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Attempt 1: clean JSON parse
    try:
        result = json.loads(raw)
        if "fixed_code" in result:
            return result
    except Exception:
        pass

    # Attempt 2: extract just the JSON object portion
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if "fixed_code" in result:
                return result
        except Exception:
            pass

    # Attempt 3: extract fixed_code directly with regex even if JSON is broken
    # Small models sometimes produce valid code but malformed surrounding JSON
    code_match = re.search(
        r'"fixed_code"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL
    )
    diagnosis_match = re.search(r'"diagnosis"\s*:\s*"([^"]*)"', raw)

    if code_match:
        # Unescape the extracted code string
        extracted_code = code_match.group(1).encode().decode('unicode_escape')
        return {
            "fix_type": "rewrite_code",
            "diagnosis": diagnosis_match.group(1) if diagnosis_match else "extracted from malformed response",
            "fixed_code": extracted_code,
        }

    # Attempt 4: if response looks like raw Python code itself, use it directly
    if raw.strip().startswith(("import ", "def ", "class ", "#")):
        return {
            "fix_type": "rewrite_code",
            "diagnosis": "model returned raw code instead of JSON",
            "fixed_code": raw.strip(),
        }

    # Nothing worked
    return {"fix_type": "skip", "diagnosis": raw[:300]}


def run_shell_command(command: str) -> tuple[bool, str]:
    """Run a shell command, return (success, output)."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=120
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


async def _run_code_with_retries(
    model_client, task: dict, goal: str, context: str, max_attempts: int = 3
) -> dict:
    """
    Generate and execute code, retrying up to max_attempts times on failure.
    Each retry gets a fresh diagnosis and rewrite.
    Returns {"result": str, "success": bool}
    """
    tid  = task["id"]
    desc = task["description"]
    code = await generate_code(model_client, goal, context)

    for attempt in range(1, max_attempts + 1):
        info(f"Attempt {attempt}/{max_attempts} — code ({len(code.splitlines())} lines):")
        info("\n".join(f"    {l}" for l in code.splitlines()[:15]) +
             ("\n    ..." if len(code.splitlines()) > 15 else ""))

        auto_install_missing(code)
        result_dict = execute_python_code(code)

        if result_dict["success"]:
            output = result_dict["stdout"] or "(no output)"
            ok(f"Code ran successfully on attempt {attempt}")
            info(output[:500])
            return {"result": output, "success": True}

        error_msg = (result_dict["error"] or result_dict["stderr"] or "unknown error").strip()
        err(f"Attempt {attempt} failed: {error_msg[:200]}")

        if attempt == max_attempts:
            err(f"All {max_attempts} attempts failed — giving up on this task")
            return {"result": f"Failed after {max_attempts} attempts. Last error: {error_msg}", "success": False}

        # Diagnose and get fixed code for next attempt
        fixing(f"Diagnosing — preparing attempt {attempt + 1}...")
        fix = await fix_task(model_client, task, error_msg, code)
        info(f"Diagnosis: {fix.get('diagnosis', '?')[:150]}")

        # Handle pip install if needed
        if fix.get("fix_type") == "run_shell_then_retry":
            cmd = fix.get("shell_command", "")
            if cmd:
                fixing(f"$ {cmd}")
                shell_ok, shell_out = run_shell_command(cmd)
                ok(f"Installed") if shell_ok else warn(shell_out[:200])

        # Get the fixed code for next iteration
        next_code = fix.get("fixed_code", "").strip()
        if next_code:
            code = next_code
        else:
            # Fixer gave no code — re-generate with error as context
            warn("Fixer provided no code — re-generating with error context")
            error_context = (
                f"{context}\n\n"
                f"Previous attempt failed with error:\n{error_msg}\n\n"
                f"Failed code was:\n{code}\n\n"
                f"Write a corrected version that avoids this error."
            )
            code = await generate_code(model_client, goal, error_context)

    return {"result": "Failed — max attempts reached", "success": False}


async def execute_task(
    model_client, task: dict, context: str, results: list[dict]
) -> dict:
    """
    Execute a single task. Returns:
        {"id": N, "description": ..., "result": ..., "success": bool}

    ── Capability map (curriculum → implementation) ──────────────
    File Agent  / Read .txt         → task type "read_txt"   → read_txt()
    File Agent  / Read .csv         → task type "read_csv"   → read_csv()
    File Agent  / Read .json        → task type "read_json"  → read_json()
    File Agent  / Write .txt        → task type "write_txt"  → write_txt()
    File Agent  / Write .csv        → task type "write_csv"  → write_csv()
                                      (DictWriter — format guaranteed)
    Code Agent  / Python execution  → task type "run_code"   → execute_python_code()
                                    + "run_shell" for installs
    DB Agent    / SQLite + SQL      → task type "query_db"   → inspect_schema()
                                                               query_database()
    ──────────────────────────────────────────────────────────────
    """
    tid   = task["id"]
    ttype = task["type"]
    args  = task.get("args", {})
    desc  = task["description"]

    step(tid, f"[{ttype}] {desc}")

    # ── read_txt ──────────────────────────────────────────────────
    if ttype == "read_txt":
        file_path = args.get("file_path", "")
        info(f"Reading text: {file_path}")
        result = read_txt(file_path)
        if result.startswith("❌"):
            err(result)
            return {"id": tid, "description": desc, "result": result, "success": False}
        ok(f"Read {file_path} ({len(result)} chars)")
        info(result[:300] + ("..." if len(result) > 300 else ""))
        return {"id": tid, "description": desc, "result": result, "success": True}

    # ── read_csv ──────────────────────────────────────────────────
    elif ttype == "read_csv":
        file_path = args.get("file_path", "")
        info(f"Reading CSV: {file_path}")
        result = read_csv(file_path)
        if not result["success"]:
            err(result["error"])
            return {"id": tid, "description": desc,
                    "result": result["error"], "success": False}
        ok(f"Read {file_path} — {result['count']} rows × {len(result['columns'])} cols")
        info(f"Columns: {', '.join(result['columns'])}")
        # Return the full display string for the answer generator,
        # but also store the structured data for use by later tasks
        display = read_file(file_path)
        return {"id": tid, "description": desc,
                "result": display, "structured": result, "success": True}

    # ── read_json ─────────────────────────────────────────────────
    elif ttype == "read_json":
        file_path = args.get("file_path", "")
        info(f"Reading JSON: {file_path}")
        result = read_json(file_path)
        if not result["success"]:
            err(result["error"])
            return {"id": tid, "description": desc,
                    "result": result["error"], "success": False}
        ok(f"Read {file_path}")
        display = json.dumps(result["data"], indent=2)
        info(display[:300])
        return {"id": tid, "description": desc,
                "result": display, "structured": result["data"], "success": True}

    # ── write_txt ─────────────────────────────────────────────────
    elif ttype == "write_txt":
        file_path = args.get("file_path", "")
        text      = args.get("text", "")

        # Always generate via the content generator — even if planner
        # inlined a short text, the generator produces better formatted output
        if text == "GENERATE" or text:
            info("Generating formatted document content...")
            # Pass both the task description AND the original user query
            # so the generator knows exactly what kind of document to write
            generation_desc = f"{desc}\n\nOriginal user request: {context.splitlines()[0] if context else desc}"
            text = await generate_file_content(model_client, generation_desc, context)
            info(f"Generated {len(text)} chars")
            info(text[:200] + ("..." if len(text) > 200 else ""))

        result = write_txt(file_path, text)
        ok(result)
        return {"id": tid, "description": desc, "result": result, "success": True}

    # ── write_csv ─────────────────────────────────────────────────
    elif ttype == "write_csv":
        file_path = args.get("file_path", "")
        rows      = args.get("rows", "GENERATE")

        if rows == "GENERATE":
            info("Generating CSV rows via LLM...")
            rows = await generate_csv_rows(model_client, desc, context)
            if rows is None:
                err("Failed to generate valid CSV rows")
                return {"id": tid, "description": desc,
                        "result": "❌ Could not generate CSV rows", "success": False}
            info(f"Generated {len(rows)} rows")
        else:
            # Rows were inlined in the plan by the planner
            info(f"Using {len(rows)} rows from plan")

        # write_csv handles both list[dict] and list[list] — format guaranteed
        result = write_csv(file_path, rows)
        if result.startswith("❌"):
            err(result)
            return {"id": tid, "description": desc, "result": result, "success": False}
        ok(result)
        return {"id": tid, "description": desc, "result": result, "success": True}

    # ── run_shell ─────────────────────────────────────────────────
    elif ttype == "run_shell":
        command = args.get("command", "").strip()
        info(f"$ {command}")
        success, output = run_shell_command(command)
        if success:
            ok("Command completed")
        else:
            warn("Command exited with error")
        if output:
            info(output[:400])
        return {"id": tid, "description": desc,
                "result": output or "(no output)", "success": success}

    # ── run_code ──────────────────────────────────────────────────
    elif ttype == "run_code":
        # goal describes what the code must do — fall back to desc if missing
        goal = args.get("goal", "").strip() or desc
        info(f"Goal: {goal}")

        outcome = await _run_code_with_retries(
            model_client, task, goal, context, max_attempts=3
        )
        return {"id": tid, "description": desc,
                "result": outcome["result"], "success": outcome["success"]}

    # ── query_db ──────────────────────────────────────────────────
    elif ttype == "query_db":
        db_path = args.get("db_path", None)
        goal    = args.get("goal", desc)

        # Always inspect schema first — gives SQL generator exact column names
        info("Inspecting schema...")
        schema = inspect_schema(db_path)
        info(schema)   # show full schema in CLI — critical for debugging

        # Generate SQL strictly from the schema
        info(f"Generating SQL for: {goal}")
        sql = await generate_sql(model_client, goal, schema)
        info(f"SQL: {sql}")

        result = query_database(sql, db_path)
        if result.startswith("❌"):
            err(result)
            fixing("Fixing SQL — re-reading schema and retrying...")
            # Pass schema again explicitly so fixer has full context
            fix_goal = (
                f"{goal}\n\n"
                f"Previous SQL that failed: {sql}\n"
                f"Error: {result}\n\n"
                f"Schema (use ONLY these exact column names):\n{schema}"
            )
            fixed_sql = await generate_sql(model_client, fix_goal, schema)
            info(f"Fixed SQL: {fixed_sql}")
            result = query_database(fixed_sql, db_path)
            if not result.startswith("❌"):
                ok("Fixed SQL worked")
                info(result[:600])
                return {"id": tid, "description": desc,
                        "result": result, "success": True}
            err(f"Retry also failed: {result}")
            return {"id": tid, "description": desc, "result": result, "success": False}

        ok("Query successful")
        info(result[:600])
        return {"id": tid, "description": desc, "result": result, "success": True}

    else:
        warn(f"Unknown task type: {ttype}")
        return {"id": tid, "description": desc,
                "result": f"Unknown task type: {ttype}", "success": False}


# ─────────────────────────────────────────────────────────────────
#  STEP 4 — ANSWER GENERATOR
#  Takes all task results, writes a clean final answer.
# ─────────────────────────────────────────────────────────────────

ANSWER_SYSTEM = """\
You are a helpful assistant writing a final answer for the user.

You have been given:
  - The user's original question
  - The results of each task that was run to answer it

Write a clear, well-structured answer based on those results.
Be helpful, concise, and accurate. Do not mention internal task IDs.\
"""

async def generate_answer(model_client, query: str, results: list[dict]) -> str:
    results_text = "\n\n".join(
        f"Task {r['id']} ({r['description']}):\n{r['result']}"
        for r in results
    )
    prompt = f"User question: {query}\n\nTask results:\n{results_text}"
    return await llm(model_client, ANSWER_SYSTEM, prompt)


# ─────────────────────────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────

async def run_pipeline(query: str, model_client):
    print(f"\n{C.BOLD}{C.CYAN}{'═'*60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  Query: {query}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═'*60}{C.RESET}")

    # 1. Plan
    tasks = await plan(model_client, query)

    # 2. Execute each task in order
    hdr("EXECUTOR — running tasks")
    results  = []
    context  = f"User query: {query}\n"

    for task in tasks:
        result = await execute_task(model_client, task, context, results)
        results.append(result)

        # Build context for the next task.
        # READ tasks pass their FULL content — truncation would mean the
        # next task (e.g. write a report) only sees partial file data.
        # Other tasks get a 500-char summary to keep context manageable.
        ttype = task.get("type", "")
        if ttype in ("read_txt", "read_csv", "read_json") and result["success"]:
            # Full content — no truncation
            context += f"\nTask {task['id']} — {task['description']}:\n{result['result']}\n"
        else:
            # Summary for non-read tasks (code output, write confirmations, etc.)
            context += f"\nTask {task['id']} — {task['description']}:\n{result['result'][:500]}\n"

    # 3. Final answer
    hdr("ANSWER")
    answer = await generate_answer(model_client, query, results)
    print(f"\n{C.BOLD}{answer}{C.RESET}\n")


# ─────────────────────────────────────────────────────────────────
#  Interactive CLI
# ─────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        DAY 3 — Tool-Calling Agent Pipeline                   ║
║        Plan → Execute → Fix → Answer                         ║
║                                                              ║
║  Type your query and press Enter.  Type 'exit' to quit.      ║
╚══════════════════════════════════════════════════════════════╝"""

EXAMPLES = """
Example queries:
  • Read the file at data/sales.csv and summarise it
  • Create a CSV of the 5 largest planets with columns name, diameter_km,
    moons — save it to data/planets.csv
  • Analyse data/sales.csv and find the top 3 products by total revenue
  • Write a short report about AI agents to data/report.txt
  • Query the database data/sales.db and show total sales per region
  • Generate a times table up to 12 using Python
"""


async def interactive_loop():
    print(BANNER)
    print(EXAMPLES)

    model_client = get_model_client()

    while True:
        try:
            print(f"\n{C.BOLD}{'─'*62}{C.RESET}")
            query = input("  Your query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exiting]")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit", "q"):
            print("[Exiting]")
            break

        await run_pipeline(query, model_client)


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    asyncio.run(interactive_loop())