from datetime import datetime
from pathlib import Path

from nexus_ai.config import WORKSPACE_DIR
from nexus_ai.task_utils import slugify_task


def create_task_workspace(
    task: str,
    workspace_dir: Path | None = None,
    folder_label: str | None = None,
) -> tuple[str, Path]:
    base_dir = workspace_dir or WORKSPACE_DIR
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = base_dir / f"{slugify_task(folder_label or task)}_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    return f"./workspace/{folder.name}", folder
