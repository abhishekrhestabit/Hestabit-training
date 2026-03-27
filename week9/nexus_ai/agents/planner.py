"""
nexus_ai/agents/planner.py  —  Planner Agent
Breaks the user task into a structured sub-task list for other agents.
"""

import json, re
from .base_agent import BaseAgent
from nexus_ai.task_utils import is_local_build_task


class PlannerAgent(BaseAgent):
    NAME = "Planner"
    ROLE = "Breaks tasks into structured execution steps"
    SYSTEM_PROMPT = """\
You are the Planner Agent in a multi-agent AI system called NEXUS.

Given a user task, produce a JSON execution plan.

OUTPUT — raw JSON object only, no fences:
{
  "task_type": "research|code|analysis|writing|mixed",
  "complexity": "simple|medium|complex",
  "agents_needed": ["Researcher", "Coder", "Analyst", "Critic", "Optimizer", "Validator", "Reporter"],
  "steps": [
    {"step": 1, "agent": "AgentName", "instruction": "specific instruction for this agent"}
  ],
  "final_output_format": "report|code|csv|answer"
}

AGENT CAPABILITIES:
  Researcher  — web search, read files, gather information
  Coder       — write and execute Python code
  Analyst     — analyse data, CSV files, databases, SQL queries
  Critic      — review quality, find gaps and errors
  Optimizer   — improve output based on critic feedback
  Validator   — final quality check, approve or flag
  Reporter    — write final structured report/answer

ROUTING RULES:
  You are the PRIMARY routing authority for this workflow.
  The orchestrator will mostly follow your plan as written.
  Do not assume the orchestrator will add, remove, or repair missing agents for you.
  If [Memory context] contains data relevant to the question:
    → Use Researcher (it will answer from memory, no web search)
    → Then Reporter. Do NOT add Analyst/Critic for simple follow-ups.
  If context says a specific file path or database path is provided:
    → Prefer Researcher for read/explain/summarise tasks
    → Prefer Analyst for structured data, SQL, CSV, or database inspection
    → Do NOT use Coder unless the user explicitly wants files changed or generated
  Local backend/API/CRUD/database generation tasks:
    → Prefer Coder first
    → Add Analyst only if data/schema inspection is genuinely needed
    → Do NOT use Researcher unless the user explicitly asks for latest/current
      information, comparisons, external references, or documentation lookups
    → For full system requests, tell Coder to create a multi-file project
      with the main modules the task implies, not a toy single-file script
    → Default pipeline is usually: Coder → Critic → Optimizer → Validator → Reporter
  CSV → SQLite → query:
    Step 1: Analyst  (read CSV, understand columns and data)
    Step 2: Coder    (create .db from CSV using Python)
    Step 3: Analyst  (inspect schema → generate SQL → run query)
    Step 4: Reporter
  Pure SQL query on existing .db → Analyst only
  Python calculations, algorithms, file generation → Coder
  Research, web search, reading files → Researcher

RULES:
  - Only include agents actually needed for this task
  - Prefer the smallest plan that can complete the task reliably
  - Be flexible: if one strong agent can do a step well, do not split it unnecessarily
  - Simple questions: 2-3 agents. Complex tasks: 4-6 agents.
  - Always end with Reporter
  - MANDATORY: Include Critic + Optimizer for ALL code generation tasks
    and ALL complex tasks (complexity = medium or complex)
  - Critic reviews the output. Optimizer fixes gaps. Both must appear
    before Validator when task_type is "code" or complexity is not "simple"
  - Instructions must be specific, not vague
  - For code tasks: Coder instructions must say "write files to disk using
    open() — do NOT start a server or run uvicorn/flask"
  - For fix plans: return only the agents needed to directly fix the flagged issue
  - For fix plans involving missing files, broken code, or wrong file outputs:
    prefer Coder
  - For fix plans involving wording, structure, explanation quality, or summarisation:
    prefer Optimizer
  - Use Researcher in fix plans only if fresh external/current information is truly required
  - Never include redundant agents just because they are available

Raw JSON only. No explanation.\
"""

    async def run(self, task: str, context: str = "") -> dict:
        """Returns a plan dict, not a string."""
        raw = await super().run(task, context)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(raw)
        except Exception:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
        if is_local_build_task(task):
            return {
                "task_type": "code",
                "complexity": "medium",
                "agents_needed": ["Coder", "Critic", "Optimizer", "Validator", "Reporter"],
                "steps": [
                    {
                        "step": 1,
                        "agent": "Coder",
                        "instruction": (
                            "Create a complete multi-file implementation for this task. "
                            "Write files to disk using open() — do NOT start a server or run uvicorn/flask."
                        ),
                    },
                    {
                        "step": 2,
                        "agent": "Critic",
                        "instruction": "Review the generated implementation for completeness, correctness, and missing modules.",
                    },
                    {
                        "step": 3,
                        "agent": "Optimizer",
                        "instruction": "Improve the implementation based on Critic feedback.",
                    },
                    {
                        "step": 4,
                        "agent": "Validator",
                        "instruction": "Check that the implementation actually fulfills the task requirements.",
                    },
                    {
                        "step": 5,
                        "agent": "Reporter",
                        "instruction": "Write a clear final summary of what was built.",
                    },
                ],
                "final_output_format": "code",
            }
        # Fallback plan
        return {
            "task_type": "mixed",
            "complexity": "medium",
            "agents_needed": ["Researcher", "Reporter"],
            "steps": [
                {"step": 1, "agent": "Researcher", "instruction": task},
                {"step": 2, "agent": "Reporter",
                 "instruction": "Write a clear answer based on research findings"},
            ],
            "final_output_format": "report",
        }
