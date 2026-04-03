from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

RATE_LIMIT_DELAY = float(os.getenv("NEXUS_RATE_LIMIT_DELAY", "2.0"))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_core.model_context import BufferedChatCompletionContext
from config import get_model_client, describe_active_model
from memory.session_memory import MemorySystem
from nexus_ai.config import AGENT_PROMPTS, RUNTIME_SETTINGS
from nexus_ai.schemas import ExecutionPlan
from tools import (
    analyze_csv, build_code_execution_tool, copy_file_to_workspace,
    describe_sqlite_table, get_source_info, inspect_csv, list_files, list_sqlite_tables,
    query_sqlite, read_text_file, set_query_folder,
    write_text_file,
)
from tools.search_tool import web_search

# ── Logging ──────────────────────────────────────────────────────────────────

_LOG_DIR = PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(_LOG_DIR / "nexus_trace.log"), level=logging.INFO, format="%(asctime)s %(message)s"
)
log = logging.getLogger("nexus")

# ── Tool registry ────────────────────────────────────────────────────────────

_WORKER_TOOLS = {
    "researcher": lambda ct: [list_files, read_text_file, inspect_csv, web_search],
    "analyst": lambda ct: [
        analyze_csv, inspect_csv, read_text_file, list_sqlite_tables,
        describe_sqlite_table, query_sqlite, write_text_file, get_source_info,
    ],
    "coder": lambda ct: (
        [list_files, read_text_file, write_text_file, copy_file_to_workspace]
        + ([ct] if ct else [])
    ),
}
_OPT_TOOLS = [list_files, read_text_file, write_text_file, get_source_info, query_sqlite]

CATEGORIES = "personal, preference, work, health, hobby, goal, general"


# ── Memory tools (mirrors Day 4 pattern) ─────────────────────────────────────

def build_memory_tools(mem: MemorySystem):
    """Create the three memory tools that agents can call."""

    async def save_core_fact(fact: str, category: str) -> str:
        """Save an important user fact to long-term memory.

        Args:
            fact:     A single plain-English sentence summarising the fact.
            category: One of: personal, preference, work, health, hobby, goal, general.
        """
        await mem.store_fact(fact, category=category)
        return f"Fact successfully saved: {fact} [category: {category}]"

    async def get_facts_by_date(date_str: str) -> str:
        """Retrieve all facts stored on a given date (YYYY-MM-DD format)."""
        facts = mem.long_term.get_facts_by_date(date_str)
        if not facts:
            return f"No facts or conversations found for {date_str}."
        lines = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
        return f"Facts/conversations from {date_str}:\n{lines}"

    async def get_facts_by_category(category: str) -> str:
        """Retrieve all facts stored under a specific category.

        Arg must be one of: personal, preference, work, health, hobby, goal, general.
        """
        facts = mem.long_term.search_by_category(category)
        if not facts:
            return f"No facts found in category '{category}'."
        lines = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
        return f"Facts in category '{category}':\n{lines}"

    return [save_core_fact, get_facts_by_date, get_facts_by_category]


# ── JSON extraction ──────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines[-1].strip() == "```":
            s = "\n".join(lines[1:-1]).strip()
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON found")

    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        ch = s[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json.loads(s[start:i + 1])
                return s[start:i + 1]

    raise ValueError("Incomplete JSON")


# ── Planning ─────────────────────────────────────────────────────────────────

async def _plan(client, query, memory, mem_tools, feedback=None) -> ExecutionPlan:
    schema = json.dumps(ExecutionPlan.model_json_schema(), indent=2)
    planner = AssistantAgent(
        "Planner",
        model_client=client,
        memory=[memory.session, memory.fact_memory],
        tools=mem_tools,
        reflect_on_tool_use=True,
        system_message=(
            f"{AGENT_PROMPTS['Planner']}\n\nSchema:\n{schema}\n\n"
            f"Today is {date.today().isoformat()}.\n"
            "If the user reveals personal facts, call `save_core_fact` ONCE PER FACT "
            f"with a category from: {CATEGORIES}.\n"
            "When the user asks about a specific topic or broad questions about themselves, "
            "call `get_facts_by_category` for each relevant category."
        ),
    )
    task = f"User request:\n{query}"
    if feedback:
        task += f"\n\nPrevious attempt feedback:\n{feedback}"
    result = await planner.run(task=task)
    await asyncio.sleep(RATE_LIMIT_DELAY)
    raw = result.messages[-1].content
    return ExecutionPlan.model_validate_json(
        _extract_json(raw if isinstance(raw, str) else str(raw))
    )


# ── Graph construction ───────────────────────────────────────────────────────

def _build_graph(client, query, plan, memory, mem_tools, code_tool):
    agents, builder = [], DiGraphBuilder()
    ti = RUNTIME_SETTINGS.max_tool_iterations
    rt_path = f".runtime/code/{plan.query_folder}"
    _buf = lambda sz=5: BufferedChatCompletionContext(buffer_size=sz)
    _agent_kw = dict(reflect_on_tool_use=False, tool_call_summary_format="{result}")

    # Worker chain
    prev = None
    for i, step in enumerate(plan.steps, 1):
        sys_msg = (
            f"Step {i}: {step.title}\n"
            f"Instructions: {step.instructions}\n"
            f"Success: {step.success_criteria}\n"
            f"Deliverables: {', '.join(step.deliverables)}\n\n"
            f"{AGENT_PROMPTS[step.worker.capitalize()].replace('{RT}', rt_path)}"
        )
        worker = AssistantAgent(
            f"Worker{i}_{step.worker}",
            model_client=client,
            tools=_WORKER_TOOLS[step.worker](code_tool),
            system_message=sys_msg,
            max_tool_iterations=max(ti, len(step.deliverables) + 2),
            **_agent_kw,
        )
        agents.append(worker)
        builder.add_node(worker)
        if prev:
            builder.add_edge(prev, worker)
        prev = worker

    # Critic
    critic = AssistantAgent(
        "Critic",
        model_client=client,
        memory=[memory.session, memory.fact_memory],
        system_message=AGENT_PROMPTS["Critic"],
        model_context=_buf(),
    )
    agents.append(critic)
    builder.add_node(critic, activation="any")
    builder.add_edge(prev, critic)

    # Optimizer (loops back to Critic if not approved)
    optimizer = AssistantAgent(
        "Optimizer",
        model_client=client,
        tools=_OPT_TOOLS + ([code_tool] if code_tool else []),
        system_message=AGENT_PROMPTS["Optimizer"].replace("{RT}", rt_path),
        max_tool_iterations=ti,
        model_context=_buf(),
        **_agent_kw,
    )
    agents.append(optimizer)
    builder.add_node(optimizer)
    builder.add_edge(
        critic, optimizer,
        condition=lambda msg: "[APPROVED]" not in str(getattr(msg, "content", "")),
    )
    builder.add_edge(optimizer, critic, activation_group="optimizer_loop")

    # Validator
    validator = AssistantAgent(
        "Validator",
        model_client=client,
        memory=[memory.session, memory.fact_memory],
        system_message=AGENT_PROMPTS["Validator"],
        model_context=_buf(),
    )
    agents.append(validator)
    builder.add_node(validator)
    builder.add_edge(critic, validator, condition="[APPROVED]")

    # Reporter
    reporter = AssistantAgent(
        "Reporter",
        model_client=client,
        memory=[memory.session, memory.fact_memory],
        tools=mem_tools,
        reflect_on_tool_use=True,
        system_message=(
            f"{AGENT_PROMPTS['Reporter']}\n\n"
            f"Today is {date.today().isoformat()}.\n"
            "After writing the report, save a summary of the completed task using "
            "`save_core_fact` with an appropriate category."
        ),
    )
    agents.append(reporter)
    builder.add_node(reporter)
    builder.add_edge(validator, reporter, condition="[VALIDATED]")

    builder.set_entry_point(agents[0])
    return GraphFlow(
        participants=agents, graph=builder.build(), max_turns=RUNTIME_SETTINGS.max_graph_turns
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find_message(result, source):
    for msg in reversed(result.messages):
        if getattr(msg, "source", "") == source:
            return str(getattr(msg, "content", ""))
    return None


def _partial_progress(result) -> str:
    completed, failed = [], []
    for msg in result.messages:
        src = getattr(msg, "source", "")
        text = str(getattr(msg, "content", ""))[:200]
        if not src or src == "user":
            continue
        if "ERROR" in text:
            failed.append(f"{src}: {text[:150]}")
        else:
            completed.append(src)

    parts = []
    if completed:
        parts.append(f"Completed: {', '.join(completed)}")
    if failed:
        parts.append("Failed:\n" + "\n".join(failed))
    return "\n".join(parts) or "No progress made."


def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return any(k in s for k in ("rate_limit", "429", "resource_exhausted"))


# ── Main execution loop ─────────────────────────────────────────────────────

async def run_nexus(query: str, memory: MemorySystem, mem_tools: list) -> str:
    client = get_model_client()
    code_tool, executor = None, None

    try:
        print(f"\n[MODEL] {describe_active_model()}")
        feedback = None

        for cycle in range(1, RUNTIME_SETTINGS.max_plan_cycles + 1):
            print(f"\n{'='*50}\n[CYCLE {cycle}] Planning...\n{'='*50}")
            plan = await _plan(client, query, memory, mem_tools, feedback)
            print(plan.model_dump_json(indent=2))
            log.info("Cycle %d: %d steps — %s", cycle, len(plan.steps), plan.plan_summary)

            # Fast path: user just shared a personal fact
            if plan.task_kind == "fact_storage":
                await memory.store_fact(
                    f"User stated: {query}",
                    category="general",
                    metadata={"query": query, "folder": plan.query_folder},
                )
                log.info("Fact stored: %s", query[:80])
                return "Got it! I've remembered that for you."

            if not plan.steps:
                feedback = "Empty plan. Create actual steps."
                continue

            # Set up workspace folder
            qf = plan.query_folder
            set_query_folder(qf)
            log.info("Query folder: %s", qf)

            # Spin up code executor if any step needs it
            if any(s.worker == "coder" for s in plan.steps):
                if executor:
                    await executor.stop()
                    code_tool, executor = None, None
                try:
                    code_tool, executor = await build_code_execution_tool(client, query_folder=qf)
                    await asyncio.sleep(RATE_LIMIT_DELAY)
                except Exception as e:
                    log.warning("Code executor unavailable: %s", e)

            # Build and run the agent graph
            print(f"\n[GRAPH] Workers({len(plan.steps)}) → Critic ↔ Optimizer → Validator → Reporter")
            team = _build_graph(client, query, plan, memory, mem_tools, code_tool)
            task = f"User request:\n{query}\n\nExecution Plan:\n{plan.model_dump_json(indent=2)}"

            try:
                result = await Console(team.run_stream(task=task))
                await asyncio.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                if _is_rate_limit(e):
                    return f"Rate limit reached — please wait and retry.\n{str(e)[:200]}"
                log.warning("Graph error cycle %d: %s", cycle, e)
                feedback = f"Graph execution failed: {str(e)[:200]}. Try a simpler approach."
                print(f"\n[ERROR] {str(e)[:200]}")
                continue

            stop = getattr(result, "stop_reason", None)
            if stop:
                log.info("Graph stop: %s", stop)
                print(f"\n[STOP] {stop}")

            # Check for final report
            reporter_out = _find_message(result, "Reporter")
            if reporter_out:
                fact = f"Query: {query}\nResult: {reporter_out[:500]}"
                if plan.query_folder:
                    fact += f"\nFiles: .runtime/code/{plan.query_folder}/"
                await memory.store_fact(
                    fact,
                    category="general",
                    metadata={"query": query, "folder": plan.query_folder},
                )
                log.info("Stored long-term fact for query: %s", query[:80])
                return reporter_out

            # Debug: who spoke?
            speakers = list(dict.fromkeys(
                getattr(m, "source", "?")
                for m in result.messages
                if getattr(m, "source", "") not in ("", "user")
            ))
            print(f"\n[DEBUG] Agents that spoke: {' → '.join(speakers)}")

            if stop and ("rate_limit" in str(stop).lower() or "429" in str(stop)):
                return f"Rate limit reached — please wait and retry.\n{stop}"

            # Prepare feedback for replanning
            val_msg = _find_message(result, "Validator")
            if val_msg:
                feedback = val_msg
            else:
                feedback = (
                    f"Graph ended before validation.\n"
                    f"Progress:\n{_partial_progress(result)}\n"
                    f"Simplify the plan."
                )
            print(f"\n[REPLAN] {feedback[:300]}")

            if cycle < RUNTIME_SETTINGS.max_plan_cycles:
                await asyncio.sleep(RATE_LIMIT_DELAY)

        return f"Max cycles ({RUNTIME_SETTINGS.max_plan_cycles}) reached.\nLast feedback: {feedback}"

    except Exception as e:
        if _is_rate_limit(e):
            return f"Rate limit reached — please wait and retry.\n{str(e)[:200]}"
        raise
    finally:
        set_query_folder(None)
        if executor:
            await executor.stop()


# ── CLI ──────────────────────────────────────────────────────────────────────

BANNER = (
    "=" * 60
    + "\n NEXUS AI — Plan → Execute → Critique → Validate → Report\n"
    " Workers: researcher, coder, analyst\n"
    " Commands: stats | clear | exit\n"
    + "=" * 60
)


async def main():
    print(BANNER)
    memory = MemorySystem(
        db_path=str(PROJECT_ROOT / "memory" / "long_term.db"),
        vector_dir=str(PROJECT_ROOT / "memory" / "vector_store"),
    )
    mem_tools = build_memory_tools(memory)

    while True:
        try:
            query = input("\n[USER] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue

        cmd = query.lower()
        if cmd in {"exit", "quit"}:
            break
        if cmd == "stats":
            print(memory.stats())
            continue
        if cmd == "clear":
            await memory.clear()
            print("[SYSTEM] All memory cleared (session + vector + long-term).")
            print(memory.stats())
            continue

        await memory.store_turn("user", query)
        result = await run_nexus(query, memory, mem_tools)
        print(f"\n{'='*60}\n{result}\n{'='*60}")
        await memory.store_turn("agent", result)

    print("\nMemory stats at exit:", memory.stats())


if __name__ == "__main__":
    asyncio.run(main())
