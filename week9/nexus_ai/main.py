from __future__ import annotations
import asyncio, json, logging, sys, os
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
    describe_sqlite_table, inspect_csv, list_files, list_sqlite_tables,
    query_sqlite, read_text_file, set_query_folder, write_analysis_report,
    write_text_file,
)
from tools.search_tool import web_search

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename="logs/nexus_trace.log", level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("nexus")

_WORKER_TOOLS = {
    "researcher": lambda ct: [list_files, read_text_file, inspect_csv, web_search],
    "analyst":    lambda ct: [analyze_csv, inspect_csv, read_text_file, list_sqlite_tables,
                              describe_sqlite_table, query_sqlite, write_text_file, write_analysis_report],
    "coder":      lambda ct: [list_files, read_text_file, write_text_file, copy_file_to_workspace] + ([ct] if ct else []),
}
_OPT_TOOLS = [list_files, read_text_file, write_text_file, write_analysis_report, query_sqlite]

def _extract_json(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines[-1].strip() == "```": s = "\n".join(lines[1:-1]).strip()
    try: json.loads(s); return s
    except json.JSONDecodeError: pass
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
            if depth == 0: json.loads(s[start:i + 1]); return s[start:i + 1]
    raise ValueError("Incomplete JSON")

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

def _build_graph(client, query, plan, memory, code_tool):
    agents, builder = [], DiGraphBuilder()
    ti = RUNTIME_SETTINGS.max_tool_iterations
    rt_path = f".runtime/code/{plan.query_folder}"
    _buf = lambda sz=5: BufferedChatCompletionContext(buffer_size=sz)
    _agent_kw = dict(reflect_on_tool_use=False, tool_call_summary_format="{result}")

    prev = None
    for i, step in enumerate(plan.steps, 1):
        sys_msg = (f"Step {i}: {step.title}\nInstructions: {step.instructions}\n"
                   f"Success: {step.success_criteria}\nDeliverables: {', '.join(step.deliverables)}\n\n"
                   f"{AGENT_PROMPTS[step.worker.capitalize()].replace('{RT}', rt_path)}")
        w = AssistantAgent(f"Worker{i}_{step.worker}", model_client=client,
                           tools=_WORKER_TOOLS[step.worker](code_tool), system_message=sys_msg,
                           max_tool_iterations=max(ti, len(step.deliverables) + 2), **_agent_kw)
        agents.append(w); builder.add_node(w)
        if prev: builder.add_edge(prev, w)
        prev = w

    critic = AssistantAgent("Critic", model_client=client,
        system_message=AGENT_PROMPTS["Critic"], model_context=_buf())
    agents.append(critic); builder.add_node(critic, activation="any"); builder.add_edge(prev, critic)

    optimizer = AssistantAgent("Optimizer", model_client=client,
        tools=_OPT_TOOLS + ([code_tool] if code_tool else []),
        system_message=AGENT_PROMPTS["Optimizer"].replace("{RT}", rt_path),
        max_tool_iterations=ti, model_context=_buf(), **_agent_kw)
    agents.append(optimizer); builder.add_node(optimizer)
    builder.add_edge(critic, optimizer, condition=lambda msg: "[APPROVED]" not in str(getattr(msg, "content", "")))
    builder.add_edge(optimizer, critic, activation_group="optimizer_loop")

    validator = AssistantAgent("Validator", model_client=client,
        system_message=AGENT_PROMPTS["Validator"], model_context=_buf())
    agents.append(validator); builder.add_node(validator)
    builder.add_edge(critic, validator, condition="[APPROVED]")

    reporter = AssistantAgent("Reporter", model_client=client,
        memory=[memory.session, memory.fact_memory], system_message=AGENT_PROMPTS["Reporter"])
    agents.append(reporter); builder.add_node(reporter)
    builder.add_edge(validator, reporter, condition="[VALIDATED]")
    builder.set_entry_point(agents[0])

    return GraphFlow(participants=agents, graph=builder.build(), max_turns=RUNTIME_SETTINGS.max_graph_turns)

def _find_message(result, source):
    for msg in reversed(result.messages):
        if getattr(msg, "source", "") == source:
            return str(getattr(msg, "content", ""))
    return None

def _partial_progress(result) -> str:
    completed, failed = [], []
    for msg in result.messages:
        src, text = getattr(msg, "source", ""), str(getattr(msg, "content", ""))[:200]
        if not src or src == "user": continue
        (failed if "ERROR" in text else completed).append(f"{src}: {text[:150]}" if "ERROR" in text else src)
    parts = []
    if completed: parts.append(f"Completed: {', '.join(completed)}")
    if failed: parts.append("Failed:\n" + "\n".join(failed))
    return "\n".join(parts) or "No progress made."

def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return any(k in s for k in ("rate_limit", "429", "resource_exhausted"))

async def run_nexus(query: str, memory: MemorySystem) -> str:
    client = get_model_client()
    code_tool, executor = None, None
    try:
        print(f"\n[MODEL] {describe_active_model()}")
        feedback = None
        for cycle in range(1, RUNTIME_SETTINGS.max_plan_cycles + 1):
            print(f"\n{'='*50}\n[CYCLE {cycle}] Planning...\n{'='*50}")
            plan = await _plan(client, query, memory, feedback)
            print(plan.model_dump_json(indent=2))
            log.info("Cycle %d: %d steps — %s", cycle, len(plan.steps), plan.plan_summary)
            if not plan.steps: feedback = "Empty plan. Create actual steps."; continue

            qf = plan.query_folder
            set_query_folder(qf); log.info("Query folder: %s", qf)

            if any(s.worker == "coder" for s in plan.steps):
                if executor: await executor.stop(); code_tool, executor = None, None
                try: code_tool, executor = await build_code_execution_tool(client, query_folder=qf); await asyncio.sleep(RATE_LIMIT_DELAY)
                except Exception as e: log.warning("Code executor unavailable: %s", e)

            print(f"\n[GRAPH] Workers({len(plan.steps)}) → Critic ↔ Optimizer → Validator → Reporter")
            team = _build_graph(client, query, plan, memory, code_tool)
            task = f"User request:\n{query}\n\nExecution Plan:\n{plan.model_dump_json(indent=2)}"
            try:
                result = await Console(team.run_stream(task=task))
                await asyncio.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                if _is_rate_limit(e): return f"Rate limit reached — please wait and retry.\n{str(e)[:200]}"
                log.warning("Graph error cycle %d: %s", cycle, e)
                feedback = f"Graph execution failed: {str(e)[:200]}. Try a simpler approach."
                print(f"\n[ERROR] {str(e)[:200]}"); continue

            stop = getattr(result, "stop_reason", None)
            if stop: log.info("Graph stop: %s", stop); print(f"\n[STOP] {stop}")

            reporter_out = _find_message(result, "Reporter")
            if reporter_out:
                fact = f"Query: {query}\nResult: {reporter_out[:500]}"
                if plan.query_folder: fact += f"\nFiles: .runtime/code/{plan.query_folder}/"
                await memory.store_fact(fact, metadata={"query": query, "folder": plan.query_folder})
                log.info("Stored long-term fact for query: %s", query[:80])
                return reporter_out

            speakers = list(dict.fromkeys(getattr(m, "source", "?") for m in result.messages if getattr(m, "source", "") not in ("", "user")))
            print(f"\n[DEBUG] Agents that spoke: {' → '.join(speakers)}")
            if stop and ("rate_limit" in str(stop).lower() or "429" in str(stop)):
                return f"Rate limit reached — please wait and retry.\n{stop}"

            val_msg = _find_message(result, "Validator")
            feedback = val_msg if val_msg else f"Graph ended before validation.\nProgress:\n{_partial_progress(result)}\nSimplify the plan."
            print(f"\n[REPLAN] {feedback[:300]}")
            if cycle < RUNTIME_SETTINGS.max_plan_cycles: await asyncio.sleep(RATE_LIMIT_DELAY)

        return f"Max cycles ({RUNTIME_SETTINGS.max_plan_cycles}) reached.\nLast feedback: {feedback}"
    except Exception as e:
        if _is_rate_limit(e): return f"Rate limit reached — please wait and retry.\n{str(e)[:200]}"
        raise
    finally:
        set_query_folder(None)
        if executor: await executor.stop()


async def main():
    print("=" * 60 + "\n NEXUS AI — Plan → Execute → Critique → Validate → Report\n"
          " Workers: researcher, coder, analyst | Type 'exit' to quit\n" + "=" * 60)
    memory = MemorySystem()
    while True:
        try:
            query = input("\n[USER] ").strip()
            if query.lower() in {"exit", "quit"}: break
            if not query: continue
            await memory.store_turn("user", query)
            result = await run_nexus(query, memory)
            print(f"\n{'='*60}\n{result}\n{'='*60}")
            await memory.store_turn("agent", result)
        except (EOFError, KeyboardInterrupt): break


if __name__ == "__main__":
    asyncio.run(main())
