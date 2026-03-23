"""
nexus_ai/main.py  —  NEXUS AI CLI
Run from the week9/ directory:  python nexus_ai/main.py
"""

import asyncio, sys, time
from pathlib import Path

# ── Path setup — allows importing tools/, memory/, config/ from parent ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nexus_ai.config       import get_model_client, ACTIVE_PROVIDER, OLLAMA_MODEL, GEMINI_MODEL
from nexus_ai.orchestrator import NexusOrchestrator
from nexus_ai.logger       import log


# ── Colours ──────────────────────────────────────────────────────
class C:
    RESET="\033[0m"; BOLD="\033[1m"; CYAN="\033[96m"; GREEN="\033[92m"
    YELLOW="\033[93m"; RED="\033[91m"; GREY="\033[90m"; PURPLE="\033[35m"
    BLUE="\033[94m"; MAGENTA="\033[95m"

def hdr(t):      print(f"\n{C.BOLD}{C.CYAN}{'─'*60}\n  {t}\n{'─'*60}{C.RESET}")
def agent_hdr(a):print(f"\n{C.BOLD}{C.BLUE}  ── {a} ──{C.RESET}")
def agent_out(t): print(f"  {C.GREY}{t}{C.RESET}")
def ok(t):       print(f"  {C.GREEN}✅ {t}{C.RESET}")
def warn(t):     print(f"  {C.YELLOW}⚠️  {t}{C.RESET}")
def err(t):      print(f"  {C.RED}❌ {t}{C.RESET}")
def info(t):     print(f"  {C.GREY}{t}{C.RESET}")
def sep():       print(f"  {C.GREY}{'·'*56}{C.RESET}")


BANNER = f"""
╔══════════════════════════════════════════════════════════════╗
║           NEXUS AI  —  Autonomous Multi-Agent System         ║
║                                                              ║
║  Agents: Planner · Researcher · Coder · Analyst              ║
║          Critic · Optimizer · Validator · Reporter           ║
║                                                              ║
║  Commands:                                                   ║
║    /file <path>   — attach a file for Researcher/Analyst     ║
║    /db   <path>   — attach a SQLite DB for Analyst           ║
║    /save <path>   — save report to file                      ║
║    /trace         — show last execution trace                ║
║    /model         — show active model                        ║
║    /memory        — show memory stats and contents           ║
║    clear          — wipe all memory layers                   ║
║    exit           — quit                                     ║
╚══════════════════════════════════════════════════════════════╝"""

EXAMPLES = """
Example tasks:
  • Plan a startup in AI for healthcare
  • Generate backend architecture for a scalable e-commerce app
  • Design a RAG pipeline for 50,000 documents
  • Write a Python script to scrape and analyse news headlines
  • /file data/sales.csv  Analyse this CSV and create a business strategy
"""


def parse_flags(query: str) -> tuple[str, dict]:
    """Extract /file, /db, /save flags from the query."""
    flags     = {"file_path": None, "db_path": None, "save_to": None}
    remaining = query

    for flag, key in [("/file", "file_path"), ("/db", "db_path"), ("/save", "save_to")]:
        if flag in remaining:
            parts = remaining.split(flag, 1)
            remaining = parts[0].strip()
            after = parts[1].strip().split()
            if after:
                flags[key] = after[0]
                remaining = (remaining + " " + " ".join(after[1:])).strip()

    return remaining, flags


_KNOWN_EXTS = {"csv","txt","md","json","db","py","yaml","yml","log","html","htm","xlsx"}

def _extract_file_from_query(query: str) -> str | None:
    """
    Python-level file path extraction — same as Day 3.
    Finds any file path mentioned in the query and checks if it exists.
    Checks: exact path → root → parent root → week9/ root
    """
    import re, os
    pattern = re.compile(
        r'(?:(?:\.{1,2}/|[\w\-]+/)*)?([\w\-]+\.[a-zA-Z0-9]{1,6})\b', re.I
    )
    for m in pattern.finditer(query):
        full  = m.group(0).strip()
        fname = m.group(1)
        ext   = fname.rsplit(".", 1)[-1].lower()
        if ext not in _KNOWN_EXTS:
            continue
        # Try to find the file — check several locations
        root = Path(__file__).resolve().parent.parent  # week9/
        candidates = [
            full,
            fname,
            str(root / full),
            str(root / fname),
            str(root / "data" / fname),
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
    return None


async def run_cli():
    print(BANNER)
    print(EXAMPLES)

    model = OLLAMA_MODEL if ACTIVE_PROVIDER == "ollama" else GEMINI_MODEL
    info(f"Provider: {ACTIVE_PROVIDER.upper()} | Model: {model}")
    info("Initialising agents...")

    client = get_model_client()
    nexus  = NexusOrchestrator(client)
    last_trace = None

    ok("NEXUS AI ready.\n")

    while True:
        try:
            print(f"\n{C.BOLD}{'─'*62}{C.RESET}")
            query = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exiting NEXUS AI]"); break

        if not query:
            continue
        if query.lower() in ("exit", "quit", "q"):
            print("[Exiting NEXUS AI]"); break

        # ── Built-in commands — never reach the pipeline ──────────
        if query.lower() in ("clear", "/clear"):
            if nexus.session or nexus.vector or nexus.ltm:
                if nexus.session: nexus.session.clear()
                if nexus.vector:  nexus.vector.clear()
                if nexus.ltm:     nexus.ltm.clear()
                ok("All memory cleared — session, vector store, and long-term DB.")
            else:
                info("Memory not available.")
            continue

        if query.lower() in ("/memory", "memory"):
            hdr("NEXUS MEMORY STATE")
            if nexus.session:
                print(f"\n  {C.PURPLE}Session memory:{C.RESET} "
                      f"{nexus.session.turn_count} turns (resets on exit)")
                nexus.session.display()
            if nexus.vector:
                print(f"\n  {C.PURPLE}Vector store:{C.RESET} "
                      f"{nexus.vector.count} entries (persists)")
                nexus.vector.display(n=5)
            if nexus.ltm:
                print(f"\n  {C.PURPLE}Long-term DB:{C.RESET} "
                      f"{nexus.ltm.count} facts (persists)")
                nexus.ltm.display(n=5)
            if not (nexus.session or nexus.vector or nexus.ltm):
                info("Memory not available.")
            continue

        if query.lower() == "/trace":
            if last_trace:
                hdr("EXECUTION TRACE")
                for step in last_trace:
                    a = step["agent"]
                    o = str(step["output"])
                    print(f"\n  {C.BOLD}[{a}]{C.RESET}")
                    print(f"  {C.GREY}{o[:400]}{'...' if len(o)>400 else ''}{C.RESET}")
            else:
                info("No trace yet.")
            continue
        if query.lower() == "/model":
            info(f"Provider: {ACTIVE_PROVIDER} | Model: {model}")
            continue

        # Parse explicit flags (/file, /db, /save)
        task, flags = parse_flags(query)
        if not task:
            info("Please provide a task."); continue

        # Auto-detect file paths mentioned in the query (like Day 3)
        if not flags["file_path"]:
            detected = _extract_file_from_query(task)
            if detected:
                flags["file_path"] = detected
                info(f"Auto-detected file: {detected}")

        # Auto-detect output file (report.md, output.txt etc in query)
        if not flags["save_to"]:
            import re
            m = re.search(r'[\w./\-]+\.(?:md|txt)', task, re.I)
            if m:
                out_name = m.group(0)
                # Only treat as save target if it's not the input file
                if out_name != flags.get("file_path"):
                    save_path = str(Path(__file__).resolve().parent.parent / out_name)
                    flags["save_to"] = save_path
                    info(f"Auto-save to: {save_path}")

        hdr(f"NEXUS — {task[:58]}")

        def on_update(step: str, content: str, output: str = ""):
            """
            Receives events from the orchestrator and prints them Day-3 style.

            step="__output__"  → full agent output (content=agent_name, output=text)
            step=agent_name    → status line (content=status message)
            """
            if step == "__output__":
                agent_name   = content
                agent_output = output
                # Agent header — blue like Day 3's step()
                print(f"\n{C.BOLD}{C.BLUE}  ┌── {agent_name} {'─'*(52-len(agent_name))}┐{C.RESET}")
                lines = agent_output.splitlines()
                for line in lines[:60]:
                    print(f"{C.BLUE}  │{C.RESET} {C.GREY}{line}{C.RESET}")
                if len(lines) > 60:
                    print(f"{C.BLUE}  │{C.RESET} {C.GREY}... ({len(lines)-60} more lines){C.RESET}")
                print(f"{C.BOLD}{C.BLUE}  └{'─'*54}┘{C.RESET}")
            else:
                # Status messages: plan list, scores, "Building...", etc.
                icons = {
                    "Critic": "🔍", "Optimizer": "🔧", "Validator": "✅",
                    "Planner": "📋", "Researcher": "🔎", "Coder": "💻",
                    "Analyst": "📊", "Reporter": "📝",
                }
                icon = icons.get(step, "·")
                print(f"  {C.PURPLE}{icon} [{step}]{C.RESET} {C.GREY}{content[:120]}{C.RESET}")

        try:
            t0     = time.time()
            result = await nexus.run(
                task      = task,
                file_path = flags["file_path"],
                db_path   = flags["db_path"],
                save_to   = flags["save_to"],
                on_update = on_update,
            )
            last_trace = result["trace"]
            duration   = time.time() - t0

            print(f"\n{'─'*62}")
            print(f"{C.BOLD}{C.CYAN}  NEXUS ANSWER{C.RESET}\n")
            print(result["answer"])
            print(f"\n{'─'*62}")
            info(f"Score: {result['score']}/10 | "
                 f"Approved: {result['approved']} | "
                 f"Time: {duration:.1f}s | "
                 f"Agents: {len(result['trace'])}")

        except Exception as e:
            err(f"Pipeline error: {e}")
            log.error("Pipeline error", error=str(e))
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_cli())