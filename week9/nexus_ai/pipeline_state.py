import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class PipelineState:
    task: str
    file_path: str | None = None
    db_path: str | None = None
    save_to: str | None = None
    on_update: Callable[[str, str, str], None] | None = None
    started_at: float = field(default_factory=time.time)
    trace: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    base_context: str = ""
    context: str = ""
    active_db_path: str | None = None
    approved: bool = True
    val_score: int = 10
    val_reason: str = ""
    unmet: list[str] = field(default_factory=list)
    final_text: str = ""
    task_workspace_rel: str = ""
    task_workspace_abs: Path | None = None

    @property
    def combined_context(self) -> str:
        parts = [self.base_context.strip(), self.context.strip()]
        return "\n\n".join(part for part in parts if part)
