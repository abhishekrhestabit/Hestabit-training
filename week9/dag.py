import asyncio
from autogen_ext.models.ollama import OllamaChatCompletionClient

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.planner import get_planner_agent
from agents.worker_agent import get_worker_agent
from agents.reflection_agent import get_reflection_agent
from agents.validator import get_validator_agent

def get_model_client():
    return OllamaChatCompletionClient(
        model="qwen2.5:3b-instruct-q4_K_M",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": True
        }
    )

def parse_plan(plan_text: str) -> list[str]:
    """Extract numbered sub-tasks from planner output."""
    lines = plan_text.strip().split("\n")
    tasks = []
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit() and "." in line:
            task = line.split(".", 1)[1].strip()
            tasks.append(task)
    return tasks


async def run_pipeline(user_query: str):
    model_client = get_model_client()

    # ── Step 1: Planner ──
    print("\n[1/4]  Planner is breaking down your query...", flush=True)
    planner = get_planner_agent(model_client)
    plan_response = await planner.run(task=user_query)
    plan_text = plan_response.messages[-1].content
    tasks = parse_plan(plan_text)

    if not tasks:
        print(" Planner returned no tasks.")
        return

    print(f"      ✔ Plan ready — {len(tasks)} sub-tasks created", flush=True)

    # ── Step 2: Parallel Workers ──
    print(f"\n[2/4]   Running {len(tasks)} workers in parallel...", flush=True)

    async def run_worker(worker_id, task):
        worker = get_worker_agent(model_client, worker_id)
        result = await worker.run(task=task)
        print(f"      ✔ Worker {worker_id} done — {task}", flush=True)
        return result.messages[-1].content
    
    
    worker_results = await asyncio.gather(*[
        run_worker(i + 1, task) for i, task in enumerate(tasks)
    ])

    # ── Step 3: Reflection ──
    print(f"\n[3/4]  Reflection Agent is synthesizing outputs...", flush=True)
    combined = "\n\n".join(worker_results)
    reflection_input = (
        f"Original Query: {user_query}\n\n"
        f"Sub-task Plan:\n{plan_text}\n\n"
        f"Worker Outputs:\n{combined}"
    )
    reflection_agent = get_reflection_agent(model_client)
    reflection_response = await reflection_agent.run(task=reflection_input)
    reflection_output = reflection_response.messages[-1].content
    print("      ✔ Synthesis complete", flush=True)

   
    # ── Step 4: Validation + Final Answer ──
    print(f"\n[4/4]  Validator is checking and generating final answer...", flush=True)
    validation_input = (
        f"Original Sub-task Plan:\n{plan_text}\n\n"
        f"Reflection Output:\n{reflection_output}"
    )
    validator = get_validator_agent(model_client)
    validation_response = await validator.run(task=validation_input)
    final_answer = validation_response.messages[-1].content

    if "VALIDATION FAILED" in final_answer.upper():
        print("\n  Validation FAILED. Please refine your query.")
        return

    print("\n" + "=" * 60)
    print("                  FINAL ANSWER")
    print("=" * 60)
    print(final_answer)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    query = input("Enter your query: ").strip()
    if not query:
        query = "Explain the applications of AI in healthcare"
    asyncio.run(run_pipeline(query))