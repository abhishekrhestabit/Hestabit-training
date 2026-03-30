from __future__ import annotations

import asyncio, json, logging, sys, os
from pathlib import Path

# Rate limiting configuration
RATE_LIMIT_DELAY = float(os.getenv("NEXUS_RATE_LIMIT_DELAY", "2.0"))  # seconds between API calls

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
    describe_sqlite_table, inspect_csv, list_files, list_sqlite_tables,
    query_sqlite, read_text_file, set_query_folder, write_analysis_report,
    write_text_file,
)
from tools.search_tool import web_search

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename="logs/nexus_trace.log", level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("nexus")

# Tool sets per worker type — matched to prompt descriptions
_WORKER_TOOLS = {
    "researcher": lambda ct: [list_files, read_text_file, inspect_csv, web_search],
    "analyst":    lambda ct: [analyze_csv, inspect_csv, read_text_file, list_sqlite_tables,
                              describe_sqlite_table, query_sqlite, write_text_file, write_analysis_report],
    "coder":      lambda ct: [list_files, read_text_file, write_text_file, copy_file_to_workspace] + ([ct] if ct else []),
}

# Optimizer — file read/write for fixes
_OPT_TOOLS = [list_files, read_text_file, write_text_file, write_analysis_report, query_sqlite]


# --- JSON extraction for planner output ---

def _extract_json(text: str) -> str:
    """Pull first valid JSON object from LLM text."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines[-1].strip() == "```": s = "\n".join(lines[1:-1]).strip()
    try:
        json.loads(s); return s
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    if start == -1: raise ValueError("No JSON found")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        ch = s[i]
        if esc: esc = False; continue
        if ch == "\\": esc = True; continue
        if ch == '"': in_str = not in_str; continue
        if in_str: continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json.loads(s[start:i + 1])
                return s[start:i + 1]
    raise ValueError("Incomplete JSON")


# --- Phase 1: Planner (runs standalone, produces JSON plan) ---

async def _plan(client, query, memory, feedback=None) -> ExecutionPlan:
    schema = json.dumps(ExecutionPlan.model_json_schema(), indent=2)
    planner = AssistantAgent("Planner", model_client=client,
        memory=[memory.session, memory.fact_memory],
        system_message=f"{AGENT_PROMPTS['Planner']}\n\nSchema:\n{schema}")
    task = f"User request:\n{query}"
    if feedback: task += f"\n\nPrevious attempt feedback:\n{feedback}"
    result = await planner.run(task=task)

    await asyncio.sleep(RATE_LIMIT_DELAY)

    raw = result.messages[-1].content
    return ExecutionPlan.model_validate_json(_extract_json(raw if isinstance(raw, str) else str(raw)))


# --- Phase 2: Build GraphFlow and execute ---

def _build_graph(client, query, plan, memory, code_tool):
    """Build a GraphFlow: Workers → Critic ↔ Optimizer → Validator → Reporter."""
    agents, builder = [], DiGraphBuilder()
    ti = RUNTIME_SETTINGS.max_tool_iterations
    rt_path = f".runtime/code/{plan.query_folder}"

    # Workers — one per plan step, chained sequentially
    prev = None
    for i, step in enumerate(plan.steps, 1):
        tools = _WORKER_TOOLS[step.worker](code_tool)
        base_prompt = AGENT_PROMPTS[step.worker.capitalize()].replace("{RT}", rt_path)
        sys_msg = (
            f"Step {i}: {step.title}\n"
            f"Instructions: {step.instructions}\n"
            f"Success: {step.success_criteria}\n"
            f"Deliverables: {', '.join(step.deliverables)}\n\n"
            f"{base_prompt}"
        )
        # Scale tool iterations: multi-file deliverables need more calls
        step_ti = max(ti, len(step.deliverables) + 2)
        # reflect_on_tool_use=False avoids "Reflect on tool use produced no valid text response" crashes
        # tool_call_summary_format gives clean output without extra LLM call
        w = AssistantAgent(f"Worker{i}_{step.worker}", model_client=client,
                           tools=tools, system_message=sys_msg,
                           reflect_on_tool_use=False,
                           tool_call_summary_format="{result}",
                           max_tool_iterations=step_ti)
        agents.append(w)
        builder.add_node(w)
        if prev: builder.add_edge(prev, w)
        prev = w

    # Critic — no tools, buffered context (only sees last 5 messages)
    critic = AssistantAgent("Critic", model_client=client,
        system_message=AGENT_PROMPTS["Critic"],
        model_context=BufferedChatCompletionContext(buffer_size=5))
    agents.append(critic)
    builder.add_node(critic, activation="any")
    builder.add_edge(prev, critic)

    # Optimizer — minimal tools, buffered context
    opt_tools = _OPT_TOOLS + ([code_tool] if code_tool else [])
    opt_prompt = AGENT_PROMPTS["Optimizer"].replace("{RT}", rt_path)
    optimizer = AssistantAgent("Optimizer", model_client=client, tools=opt_tools,
                                system_message=opt_prompt,
                                reflect_on_tool_use=False,
                                tool_call_summary_format="{result}",
                                max_tool_iterations=ti,
                                model_context=BufferedChatCompletionContext(buffer_size=5))
    agents.append(optimizer)
    builder.add_node(optimizer)

    # Critic → Optimizer (if not approved), Optimizer → Critic (loop back)
    builder.add_edge(critic, optimizer, condition=lambda msg: "[APPROVED]" not in str(getattr(msg, "content", "")))
    # IMPORTANT: separate activation_group so the loop-back edge doesn't block
    # the initial Worker→Critic edge (default "all" requires ALL edges to fire)
    builder.add_edge(optimizer, critic, activation_group="optimizer_loop")

    # Validator — no tools, buffered context
    validator = AssistantAgent("Validator", model_client=client,
        system_message=AGENT_PROMPTS["Validator"],
        model_context=BufferedChatCompletionContext(buffer_size=5))
    agents.append(validator)
    builder.add_node(validator)
    builder.add_edge(critic, validator, condition="[APPROVED]")

    # Reporter — NO buffer, needs full conversation to give accurate final answer
    reporter = AssistantAgent("Reporter", model_client=client,
        memory=[memory.session, memory.fact_memory],
        system_message=AGENT_PROMPTS["Reporter"])
    agents.append(reporter)
    builder.add_node(reporter)
    builder.add_edge(validator, reporter, condition="[VALIDATED]")

    builder.set_entry_point(agents[0])

    return GraphFlow(
        participants=agents, graph=builder.build(),
        max_turns=RUNTIME_SETTINGS.max_graph_turns,
    )


def _find_message(result, source):
    """Find last message from a given agent in the result."""
    for msg in reversed(result.messages):
        if getattr(msg, "source", "") == source:
            return str(getattr(msg, "content", ""))
    return None


def _partial_progress(result) -> str:
    """Extract what workers completed from a partial result for replan feedback."""
    completed, failed = [], []
    for msg in result.messages:
        src = getattr(msg, "source", "")
        text = str(getattr(msg, "content", ""))[:200]
        if not src or src == "user": continue
        if "ERROR" in text:
            failed.append(f"{src}: {text[:150]}")
        else:
            completed.append(src)
    parts = []
    if completed: parts.append(f"Completed: {', '.join(completed)}")
    if failed: parts.append(f"Failed:\n" + "\n".join(failed))
    return "\n".join(parts) or "No progress made."


def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return "rate_limit" in s or "429" in s or "resource_exhausted" in s


# --- Main runtime ---

async def run_nexus(query: str, memory: MemorySystem) -> str:
    """Outer loop: Plan → GraphFlow(Workers→Critic↔Optimizer→Validator→Reporter) → Replan if needed."""
    client = get_model_client()
    code_tool, executor = None, None

    try:
        print(f"\n[MODEL] {describe_active_model()}")
        feedback = None

        for cycle in range(1, RUNTIME_SETTINGS.max_plan_cycles + 1):
            # PLAN
            print(f"\n{'=' * 50}\n[CYCLE {cycle}] Planning...\n{'=' * 50}")
            plan = await _plan(client, query, memory, feedback)
            print(plan.model_dump_json(indent=2))
            log.info("Cycle %d: %d steps — %s", cycle, len(plan.steps), plan.plan_summary)

            if not plan.steps:
                feedback = "Empty plan. Create actual steps."
                continue

            # Set query folder for all file writes
            qf = plan.query_folder
            set_query_folder(qf)
            log.info("Query folder: %s", qf)

            # Init code executor lazily if any coder step (rebuild per query folder)
            if any(s.worker == "coder" for s in plan.steps):
                if executor:
                    await executor.stop()
                    code_tool, executor = None, None
                try:
                    code_tool, executor = await build_code_execution_tool(client, query_folder=qf)
                    await asyncio.sleep(RATE_LIMIT_DELAY)
                except Exception as e:
                    log.warning("Code executor unavailable: %s", e)

            # EXECUTE via GraphFlow
            print(f"\n[GRAPH] Workers({len(plan.steps)}) → Critic ↔ Optimizer → Validator → Reporter")
            team = _build_graph(client, query, plan, memory, code_tool)
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

            # Check if Reporter produced output (= fully validated)
            reporter_out = _find_message(result, "Reporter")
            if reporter_out:
                # Store completed task as long-term fact for future retrieval
                fact = f"Query: {query}\nResult: {reporter_out[:500]}"
                if plan.query_folder:
                    fact += f"\nFiles: .runtime/code/{plan.query_folder}/"
                await memory.store_fact(fact, metadata={"query": query, "folder": plan.query_folder})
                log.info("Stored long-term fact for query: %s", query[:80])
                return reporter_out

            # Debug: show which agents spoke
            speakers = [getattr(m, "source", "?") for m in result.messages if getattr(m, "source", "") not in ("", "user")]
            unique_speakers = list(dict.fromkeys(speakers))
            print(f"\n[DEBUG] Agents that spoke: {' → '.join(unique_speakers)}")

            # Check if rate limit stopped the graph mid-run
            if stop and ("rate_limit" in str(stop).lower() or "429" in str(stop)):
                return f"Rate limit reached — please wait and retry.\n{stop}"

            # Extract what worked and what didn't for replanning
            val_msg = _find_message(result, "Validator")
            progress = _partial_progress(result)
            if val_msg:
                feedback = val_msg
            else:
                feedback = f"Graph ended before validation.\nProgress:\n{progress}\nSimplify the plan."
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


async def main():
    print("=" * 60)
    print(" NEXUS AI — Plan → Execute → Critique → Validate → Report")
    print(" Workers: researcher, coder, analyst | Type 'exit' to quit")
    print("=" * 60)
    memory = MemorySystem()
    while True:
        try:
            query = input("\n[USER] ").strip()
            if query.lower() in {"exit", "quit"}: break
            if not query: continue
            await memory.store_turn("user", query)
            result = await run_nexus(query, memory)
            print("\n" + "=" * 60)
            print(result)
            print("=" * 60)
            await memory.store_turn("agent", result)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    asyncio.run(main())
