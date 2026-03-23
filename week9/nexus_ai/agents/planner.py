"""
nexus_ai/agents/planner.py  —  Planner Agent
Breaks the user task into a structured sub-task list for other agents.
"""

import json, re
from .base_agent import BaseAgent


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
  If [Memory context] contains data relevant to the question:
    → Use Researcher (it will answer from memory, no web search)
    → Then Reporter. Do NOT add Analyst/Critic for simple follow-ups.
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
  - Simple questions: 2-3 agents. Complex tasks: 4-6 agents.
  - Always end with Reporter
  - MANDATORY: Include Critic + Optimizer for ALL code generation tasks
    and ALL complex tasks (complexity = medium or complex)
  - Critic reviews the output. Optimizer fixes gaps. Both must appear
    before Validator when task_type is "code" or complexity is not "simple"
  - Instructions must be specific, not vague
  - For code tasks: Coder instructions must say "write files to disk using
    open() — do NOT start a server or run uvicorn/flask"

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