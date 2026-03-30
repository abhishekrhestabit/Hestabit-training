from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

WorkerType = Literal["researcher", "coder", "analyst"]
TaskKind = Literal["simple_answer", "artifact", "mixed"]


class PlanStep(BaseModel):
    step_id: str = Field(description="Short unique id such as step_1.")
    title: str = Field(description="Short step title.")
    worker: WorkerType = Field(description="The worker who should execute this step.")
    instructions: str = Field(description="Concrete instructions for the selected worker.")
    success_criteria: str = Field(description="What success looks like for this step.")
    deliverables: list[str] = Field(default_factory=list, description="Expected file paths or outputs.")
    depends_on: list[str] = Field(default_factory=list, description="Earlier step ids that must finish first.")


class ExecutionPlan(BaseModel):
    plan_summary: str = Field(description="Short summary of the overall plan.")
    task_kind: TaskKind = Field(description="Whether the task is a simple answer, an artifact, or both.")
    finish_condition: str = Field(description="How the validator should know the request is satisfied.")
    query_folder: str = Field(description="One-word lowercase folder name inferred from the query (e.g. 'todo', 'sales', 'weather'). All output files go here.")
    steps: list[PlanStep] = Field(description="Sequential worker steps to execute.")
