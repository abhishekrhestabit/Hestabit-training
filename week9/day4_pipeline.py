"""
day4_pipeline.py
─────────────────────────────────────────────────────────────────
Day 4 — Memory-Augmented Agent Pipeline

Extends Day 3's Plan→Execute→Fix→Answer pipeline with three
memory layers that make the agent remember across queries:

    ┌─────────────────────────────────────────────────────┐
    │  New Query                                          │
    │      ↓                                              │
    │  RECALL — search all 3 memory layers                │
    │      ↓                                              │
    │  INJECT — prepend relevant context to task          │
    │      ↓                                              │
    │  PLAN → EXECUTE → FIX → ANSWER  (Day 3 pipeline)   │
    │      ↓                                              │
    │  STORE — save query+answer into all 3 layers        │
    │      ↓                                              │
    │  User sees answer  →  next query                    │
    └─────────────────────────────────────────────────────┘

Memory layers:
    session_memory  — RAM, current session conversation window
    vector_store    — FAISS semantic similarity search (persistent)
    long_term.db    — SQLite fact store (persistent)
─────────────────────────────────────────────────────────────────
"""

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
from memory.session_memory import SessionMemory
from memory.vector_store   import VectorStore
from memory.long_term      import LongTermMemory


# ─────────────────────────────────────────────────────────────────
#  Colour helpers (same as Day 3)
# ─────────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    GREY    = "\033[90m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    PURPLE  = "\033[35m"

def hdr(text):    print(f"\n{C.BOLD}{C.CYAN}{'─'*60}{C.RESET}\n{C.BOLD}{C.CYAN}  {text}{C.RESET}\n{'─'*60}")
def ok(text):     print(f"  {C.GREEN}✅ {text}{C.RESET}")
def warn(text):   print(f"  {C.YELLOW}⚠️  {text}{C.RESET}")
def err(text):    print(f"  {C.RED}❌ {text}{C.RESET}")
def info(text):   print(f"  {C.GREY}{text}{C.RESET}")
def step(n, t):   print(f"\n{C.BOLD}{C.BLUE}  [{n}] {t}{C.RESET}")
def fixing(t):    print(f"  {C.MAGENTA}🔧 {t}{C.RESET}")
def memory(text): print(f"  {C.PURPLE}🧠 {text}{C.RESET}")


# ─────────────────────────────────────────────────────────────────
#  LLM call helper
# ─────────────────────────────────────────────────────────────────

async def llm(model_client, system: str, user: str) -> str:
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
#  STEP 0 — MEMORY RECALL
#  Runs before planning. Enriches the query with past context.
# ─────────────────────────────────────────────────────────────────

async def recall_and_inject(
    model_client,
    session: SessionMemory,
    vector:  VectorStore,
    ltm:     LongTermMemory,
    query:   str,
) -> str:
    """
    Search all three memory layers for context relevant to the query.
    Each layer owns its own recall method — no manager needed.
    Returns the enriched query string.
    """
    hdr("MEMORY — recalling relevant context")

    parts = []

    # Layer 1 — session_memory owns session recall
    session_ctx = session.recall_context()
    if session_ctx:
        parts.append(session_ctx)

    # Layer 2 — vector_store owns semantic recall
    vector_ctx = vector.recall_context(query)
    if vector_ctx:
        parts.append(vector_ctx)

    # Layer 3 — long_term owns keyword recall
    ltm_ctx = ltm.get_as_context(keyword=query.split()[0] if query else "")
    if ltm_ctx:
        parts.append(ltm_ctx)

    if not parts:
        memory("No relevant memories found — proceeding fresh.")
        return query

    context = "\n\n".join(parts)
    memory(f"Found context:\n{context[:400]}{'...' if len(context) > 400 else ''}")

    SUMMARISE_SYSTEM = """\
You are a memory assistant. Summarise the provided context into 2-3 sentences
directly relevant to the user's current query. Be concise. No preamble.\
"""
    summary = await llm(
        model_client, SUMMARISE_SYSTEM,
        f"User query: {query}\n\nRelevant past context:\n{context}",
    )

    enriched = f"{query}\n\n[Memory context — use this if relevant]\n{summary}"
    memory(f"Injected: {summary[:200]}")
    return enriched


# ─────────────────────────────────────────────────────────────────
#  STEP 1 — PLANNER  (same two-phase approach as Day 3)
# ─────────────────────────────────────────────────────────────────

THINKER_SYSTEM = """\
You are an expert at understanding what a user request truly requires.
Analyse the request and answer concisely:
1. DATA SOURCE — existing file? database? general knowledge? computation?
2. OUTPUT — file saved to disk? printed answer? both?
3. STEPS NEEDED — minimal sequence of operations.
Be concise. No JSON yet.\
"""

PLANNER_SYSTEM = """\
You are a task planner. Convert the reasoning into a minimal JSON task list.

TASK TYPES:
  read_txt    — read .txt/.md/.py/.yaml file
  read_csv    — read .csv into structured data
  read_json   — read .json file
  write_txt   — write .txt/.md/.py file  (text: "GENERATE")
  write_csv   — write .csv  (rows: "GENERATE" or inline list of dicts)
  run_code    — execute Python  (goal: specific description)
  run_shell   — shell command  (command: exact string)
  query_db    — SQLite query  (db_path, goal: plain English)

Output raw JSON array only. No fences. No explanation.
Each element: {"id":1,"type":"...","description":"...","args":{...}}

CRITICAL RULES:
  1. Only use read_* if user explicitly mentioned that file path.
  2. write_txt text must ALWAYS be "GENERATE".
  3. write_csv rows can be inline list of dicts if you know the data.
  4. run_code goal must be specific — never vague like "analyze file".
  5. query_db only if a .db file was mentioned.\
"""

async def plan(model_client, query: str) -> list[dict]:
    hdr("PLANNER — building task list")

    thinking = await llm(model_client, THINKER_SYSTEM, f"User request: {query}")
    info(f"Reasoning:\n{thinking}\n")

    raw = await llm(
        model_client,
        PLANNER_SYSTEM,
        f"User request: {query}\n\nReasoning:\n{thinking}\n\nProduce the JSON task list:",
    )
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    info(f"Raw plan:\n{raw}")

    tasks = None
    try:
        parsed = json.loads(raw)
        tasks  = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            try:
                tasks = json.loads(match.group())
            except Exception:
                pass

    if not tasks:
        warn("Plan parse failed — using single-task fallback")
        q = query.lower()
        if ".csv" in q and any(w in q for w in ("create", "write", "make", "generate")):
            m  = re.search(r'[\w./]+\.csv', query)
            fp = m.group() if m else "data/output.csv"
            tasks = [{"id":1,"type":"write_csv","description":query,"args":{"file_path":fp,"rows":"GENERATE"}}]
        elif ".csv" in q:
            m  = re.search(r'[\w./]+\.csv', query)
            fp = m.group() if m else "data/output.csv"
            tasks = [{"id":1,"type":"read_csv","description":query,"args":{"file_path":fp}}]
        else:
            tasks = [{"id":1,"type":"write_txt","description":query,"args":{"file_path":"data/answer.txt","text":"GENERATE"}}]

    print()
    for t in tasks:
        print(f"  {C.BOLD}Task {t['id']}{C.RESET}: [{t['type']}] {t['description']}")
    return tasks


# ─────────────────────────────────────────────────────────────────
#  STEP 2 — GENERATORS
# ─────────────────────────────────────────────────────────────────

CODE_GEN_SYSTEM = """\
You are a Python code writer. Write complete, runnable Python code.
Use print() for every output. You may use any library — missing packages
are auto-installed. Output ONLY raw Python. No fences.\
"""

async def generate_code(model_client, goal: str, context: str) -> str:
    code = await llm(model_client, CODE_GEN_SYSTEM,
                     f"Goal: {goal}\n\nContext:\n{context}")
    return re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()


SQL_GEN_SYSTEM = """\
You are a SQLite expert. Write a single correct SQL query.
Use ONLY column names from the schema. No explanation. No markdown. No semicolon.\
"""

async def generate_sql(model_client, goal: str, schema: str) -> str:
    sql = await llm(model_client, SQL_GEN_SYSTEM,
                    f"Schema:\n{schema}\n\nGoal: {goal}\n\nSQL:")
    return re.sub(r"```(?:sql)?", "", sql).strip().rstrip(";`").strip()


CONTENT_GEN_SYSTEM = """\
You are a professional writer. Write high-quality file content.

For .py  → clean runnable Python with docstring and comments
For .md  → full Markdown: # Title, ## sections, **bold**, bullet lists
For .txt → structured text with headings and bullets, min 300 words
For .yaml → valid YAML with comments

Start directly with content. No "Here is the file:" preamble. No wrapping fences.\
"""

async def generate_file_content(model_client, description: str, context: str) -> str:
    content = await llm(model_client, CONTENT_GEN_SYSTEM,
                        f"Write: {description}\n\nContext:\n{context}")
    content = re.sub(r"^```[\w]*\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n?```\s*$", "", content, flags=re.MULTILINE)
    return content.strip()


CSV_ROWS_SYSTEM = """\
Generate CSV rows as a JSON array of objects.
Output raw JSON array only — no fences, no explanation.
Every object must have the same keys. Values = strings or numbers.
Example: [{"name":"Earth","moons":1},{"name":"Mars","moons":2}]\
"""

async def generate_csv_rows(model_client, description: str, context: str) -> list[dict] | None:
    raw = await llm(model_client, CSV_ROWS_SYSTEM,
                    f"Generate rows for: {description}\n\nContext:\n{context}")
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        rows = json.loads(raw)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows
    except Exception:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


# ─────────────────────────────────────────────────────────────────
#  STEP 3 — FIX  (up to 3 retries)
# ─────────────────────────────────────────────────────────────────

FIX_SYSTEM = """\
A Python task failed. Provide the fixed code.
Output JSON: {"diagnosis":"...","fix_type":"rewrite_code","fixed_code":"..."}
For ModuleNotFoundError add: "shell_command":"pip install X", "fix_type":"run_shell_then_retry"
Raw JSON only. No fences. fixed_code must be complete runnable Python.\
"""

async def fix_task(model_client, task: dict, error: str, code: str) -> dict:
    raw = await llm(model_client, FIX_SYSTEM,
                    f"Goal: {task.get('description','')}\nError:\n{error}\nCode:\n{code}")
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    for attempt in [
        lambda: json.loads(raw),
        lambda: json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group()),
    ]:
        try:
            result = attempt()
            if "fixed_code" in result:
                return result
        except Exception:
            pass

    # Try extracting code directly
    m = re.search(r'"fixed_code"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
    if m:
        try:
            return {"fix_type": "rewrite_code", "fixed_code": m.group(1).encode().decode('unicode_escape')}
        except Exception:
            pass

    if raw.strip().startswith(("import ", "def ", "class ", "#")):
        return {"fix_type": "rewrite_code", "fixed_code": raw.strip()}

    return {"fix_type": "skip", "diagnosis": raw[:200]}


def run_shell_command(command: str) -> tuple[bool, str]:
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


async def run_code_with_retries(model_client, task: dict, goal: str, context: str) -> dict:
    code = await generate_code(model_client, goal, context)
    for attempt in range(1, 4):
        info(f"Attempt {attempt}/3  ({len(code.splitlines())} lines)")
        auto_install_missing(code)
        result = execute_python_code(code)
        if result["success"]:
            ok(f"Code succeeded on attempt {attempt}")
            info(result["stdout"][:500])
            return {"result": result["stdout"] or "(no output)", "success": True}

        error_msg = (result["error"] or result["stderr"] or "unknown").strip()
        err(f"Attempt {attempt} failed: {error_msg[:150]}")

        if attempt == 3:
            return {"result": f"Failed after 3 attempts. Last error: {error_msg}", "success": False}

        fixing(f"Diagnosing for attempt {attempt + 1}...")
        fix = await fix_task(model_client, task, error_msg, code)

        if fix.get("fix_type") == "run_shell_then_retry":
            cmd = fix.get("shell_command", "")
            if cmd:
                fixing(f"$ {cmd}")
                ok_shell, _ = run_shell_command(cmd)
                ok("Installed") if ok_shell else warn("Install had issues")

        next_code = fix.get("fixed_code", "").strip()
        if next_code:
            code = next_code
        else:
            code = await generate_code(
                model_client, goal,
                f"{context}\n\nPrevious error:\n{error_msg}\n\nFailed code:\n{code}"
            )

    return {"result": "Failed", "success": False}


# ─────────────────────────────────────────────────────────────────
#  STEP 4 — EXECUTOR
# ─────────────────────────────────────────────────────────────────

async def execute_task(model_client, task: dict, context: str, results: list) -> dict:
    tid   = task["id"]
    ttype = task["type"]
    args  = task.get("args", {})
    desc  = task["description"]

    step(tid, f"[{ttype}] {desc}")

    if ttype == "read_txt":
        file_path = args.get("file_path", "")
        info(f"Reading: {file_path}")
        result = read_txt(file_path)
        if result.startswith("❌"):
            err(result); return {"id": tid, "description": desc, "result": result, "success": False}
        ok(f"Read {file_path} ({len(result)} chars)")
        info(result[:300] + ("..." if len(result) > 300 else ""))
        return {"id": tid, "description": desc, "result": result, "success": True}

    elif ttype == "read_csv":
        file_path = args.get("file_path", "")
        info(f"Reading CSV: {file_path}")
        result = read_csv(file_path)
        if not result["success"]:
            err(result["error"]); return {"id": tid, "description": desc, "result": result["error"], "success": False}
        ok(f"{result['count']} rows × {len(result['columns'])} cols")
        display = read_file(file_path)
        return {"id": tid, "description": desc, "result": display, "structured": result, "success": True}

    elif ttype == "read_json":
        file_path = args.get("file_path", "")
        info(f"Reading JSON: {file_path}")
        result = read_json(file_path)
        if not result["success"]:
            err(result["error"]); return {"id": tid, "description": desc, "result": result["error"], "success": False}
        import json as _json
        display = _json.dumps(result["data"], indent=2)
        ok(f"Read {file_path}")
        return {"id": tid, "description": desc, "result": display, "success": True}

    elif ttype == "write_txt":
        file_path = args.get("file_path", "")
        text      = args.get("text", "")
        info("Generating formatted document...")
        gen_desc = f"{desc}\n\nOriginal request: {context.splitlines()[0] if context else desc}"
        text = await generate_file_content(model_client, gen_desc, context)
        info(f"Generated {len(text)} chars")
        info(text[:200] + ("..." if len(text) > 200 else ""))
        result = write_txt(file_path, text)
        ok(result)
        return {"id": tid, "description": desc, "result": result, "success": True}

    elif ttype == "write_csv":
        file_path = args.get("file_path", "")
        rows      = args.get("rows", "GENERATE")
        if rows == "GENERATE":
            info("Generating CSV rows...")
            rows = await generate_csv_rows(model_client, desc, context)
            if rows is None:
                err("Failed to generate rows")
                return {"id": tid, "description": desc, "result": "❌ Could not generate CSV rows", "success": False}
            info(f"Generated {len(rows)} rows")
        else:
            info(f"Using {len(rows)} rows from plan")
        result = write_csv(file_path, rows)
        if result.startswith("❌"):
            err(result); return {"id": tid, "description": desc, "result": result, "success": False}
        ok(result)
        return {"id": tid, "description": desc, "result": result, "success": True}

    elif ttype == "run_shell":
        command = args.get("command", "").strip()
        info(f"$ {command}")
        success, output = run_shell_command(command)
        ok("Done") if success else warn("Had errors")
        if output: info(output[:400])
        return {"id": tid, "description": desc, "result": output or "(no output)", "success": success}

    elif ttype == "run_code":
        goal = args.get("goal", "").strip() or desc
        info(f"Goal: {goal}")
        outcome = await run_code_with_retries(model_client, task, goal, context)
        return {"id": tid, "description": desc, "result": outcome["result"], "success": outcome["success"]}

    elif ttype == "query_db":
        db_path = args.get("db_path", None)
        goal    = args.get("goal", desc)
        info("Inspecting schema...")
        schema = inspect_schema(db_path)
        info(schema)
        info(f"Generating SQL for: {goal}")
        sql = await generate_sql(model_client, goal, schema)
        info(f"SQL: {sql}")
        result = query_database(sql, db_path)
        if result.startswith("❌"):
            err(result)
            fixing("Retrying with error context...")
            sql2 = await generate_sql(
                model_client,
                f"{goal}\n\nFailed SQL: {sql}\nError: {result}\nUse ONLY column names from schema above.",
                schema,
            )
            result = query_database(sql2, db_path)
            if result.startswith("❌"):
                return {"id": tid, "description": desc, "result": result, "success": False}
        ok("Query successful")
        info(result[:600])
        return {"id": tid, "description": desc, "result": result, "success": True}

    else:
        warn(f"Unknown task type: {ttype}")
        return {"id": tid, "description": desc, "result": f"Unknown: {ttype}", "success": False}


# ─────────────────────────────────────────────────────────────────
#  STEP 5 — ANSWER GENERATOR
# ─────────────────────────────────────────────────────────────────

ANSWER_SYSTEM = """\
You are a helpful assistant. Write a clear, well-structured final answer
based on the task results provided. Be concise and useful.\
"""

async def generate_answer(model_client, query: str, results: list[dict]) -> str:
    results_text = "\n\n".join(
        f"Task {r['id']} ({r['description']}):\n{r['result']}" for r in results
    )
    return await llm(model_client, ANSWER_SYSTEM,
                     f"User question: {query}\n\nTask results:\n{results_text}")


# ─────────────────────────────────────────────────────────────────
#  STEP 6 — MEMORY STORE
#  After the answer is ready, extract facts and persist everything.
# ─────────────────────────────────────────────────────────────────

async def extract_and_store_facts(
    model_client,
    session: SessionMemory,
    vector:  VectorStore,
    ltm:     LongTermMemory,
    query:   str,
    answer:  str,
) -> None:
    """
    Persist the completed Q&A across all three memory layers.
    Each layer owns its own store method — no manager needed.

    session_memory  ← both turns (add_user + add_assistant)
    vector_store    ← store_episode (embeds Q + A for semantic search)
    long_term       ← store_episode (SQL rows for keyword search)

    Also extracts 1-3 facts and stores those as semantic memories.
    """
    hdr("MEMORY — storing new knowledge")

    # Layer 1: session_memory owns ephemeral turn storage
    session.add_user(query)
    session.add_assistant(answer)
    memory("Session turns stored")

    # Layer 2: vector_store owns semantic episode + fact storage
    vector.store_episode(query, answer)
    memory("Vector embeddings stored")

    # Layer 3: long_term owns persistent SQL episode storage
    ltm.store_episode(query, answer)
    memory("Long-term DB rows stored")

    # Extract and store semantic facts (best-effort — never breaks pipeline)
    FACT_EXTRACT_SYSTEM = """\
Extract 1-3 short, specific, reusable facts from this Q&A.
Each fact = one sentence. Output as JSON array of strings.
Example: ["Widget B had the highest revenue at $550"]
Raw JSON only. No fences.\
"""
    raw = await llm(model_client, FACT_EXTRACT_SYSTEM,
                    f"Question: {query}\n\nAnswer: {answer[:800]}")
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        facts = json.loads(raw)
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, str) and fact.strip():
                    vector.store_fact(fact.strip())       # semantic
                    ltm.store(fact.strip(), source="fact") # keyword
                    memory(f"Fact stored: {fact[:100]}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────

async def run_pipeline(
    query:   str,
    model_client,
    session: SessionMemory,
    vector:  VectorStore,
    ltm:     LongTermMemory,
):
    print(f"\n{C.BOLD}{C.CYAN}{'═'*60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  Query: {query}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═'*60}{C.RESET}")

    # 0. Recall from all three layers
    enriched_query = await recall_and_inject(model_client, session, vector, ltm, query)

    # 1. Plan
    tasks = await plan(model_client, enriched_query)

    # 2. Execute
    hdr("EXECUTOR — running tasks")
    results = []
    context = f"User query: {query}\n"

    for task in tasks:
        result = await execute_task(model_client, task, context, results)
        results.append(result)
        ttype = task.get("type", "")
        if ttype in ("read_txt", "read_csv", "read_json") and result["success"]:
            context += f"\nTask {task['id']} — {task['description']}:\n{result['result']}\n"
        else:
            context += f"\nTask {task['id']} — {task['description']}:\n{result['result'][:500]}\n"

    # 3. Answer
    hdr("ANSWER")
    answer = await generate_answer(model_client, query, results)
    print(f"\n{C.BOLD}{answer}{C.RESET}\n")

    # 4. Store into all three layers
    await extract_and_store_facts(model_client, session, vector, ltm, query, answer)

    return answer


# ─────────────────────────────────────────────────────────────────
#  Interactive CLI
# ─────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        DAY 4 — Memory-Augmented Agent Pipeline               ║
║        Plan → Execute → Fix → Answer → Remember              ║
║                                                              ║
║  Commands:  'memory' = show memory stats                     ║
║             'clear'  = wipe all memory                       ║
║             'exit'   = quit                                  ║
╚══════════════════════════════════════════════════════════════╝"""

EXAMPLES = """
Try these queries (memory carries across them!):
  • Read data/sales.csv and summarise it
  • What was the highest revenue product?         ← tests memory recall
  • Create a CSV of the 5 largest planets — save to data/planets.csv
  • What files have we created today?             ← tests episodic memory
  • Write a report about AI memory systems to data/memory-report.md
  • Query the database data/sales.db for total per region
"""


async def interactive_loop():
    print(BANNER)
    print(EXAMPLES)

    model_client = get_model_client()

    # Three memory objects — each is a curriculum deliverable
    # vector_store and long_term.db persist to disk across sessions
    session = SessionMemory(window=10)
    vector  = VectorStore(store_path="memory", top_k=3)
    ltm     = LongTermMemory(db_path="memory/long_term.db")

    print(f"\n  Memory: {session.turn_count} session turns | "
          f"{vector.count} vectors | {ltm.count} facts\n")

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

        if query.lower() == "memory":
            session.display()
            vector.display()
            ltm.display()
            print(f"  Stats: session={session.turn_count} turns | "
                  f"vectors={vector.count} | facts={ltm.count}")
            continue

        if query.lower() == "clear":
            session.clear()
            vector.clear()
            ltm.clear()
            print("  All memory cleared.")
            continue

        print()
        await run_pipeline(query, model_client, session, vector, ltm)


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    Path("memory").mkdir(exist_ok=True)
    asyncio.run(interactive_loop())