from __future__ import annotations
import re, shutil
from pathlib import Path

import pandas as pd
from autogen_agentchat.agents import AssistantAgent
from typing_extensions import Annotated

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_CODE_DIR = PROJECT_ROOT / ".runtime" / "code"
IGNORED_DIRS = {".git", ".runtime", "__pycache__", "venv"}
DEFAULT_FILE_LIST_LIMIT = 50
DEFAULT_TEXT_PREVIEW_CHARS = 6000
_active_query_folder: str | None = None

# Sets the active query folder for scoping file reads/writes to a subdirectory of .runtime/code.
def set_query_folder(folder_name: str | None) -> None:
    global _active_query_folder
    _active_query_folder = folder_name
    if folder_name: (RUNTIME_CODE_DIR / folder_name).mkdir(parents=True, exist_ok=True)

# Resolves a relative output path to an absolute path inside the active query folder or project root.
def _resolve_write_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute(): return candidate.resolve()
    if _active_query_folder: return (RUNTIME_CODE_DIR / _active_query_folder / candidate).resolve()
    return (PROJECT_ROOT / candidate).resolve()

# Resolves any path (including Docker /workspace/ paths) to an absolute host path.
def _resolve_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if str(candidate).startswith("/workspace/"):
        base = RUNTIME_CODE_DIR / _active_query_folder if _active_query_folder else RUNTIME_CODE_DIR
        return (base / str(candidate)[len("/workspace/"):]).resolve()
    return candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()

# Atomically writes or copies a file to the destination using a temp file to avoid partial writes.
def _replace_file(destination: Path, *, text: str | None = None, source: Path | None = None) -> None:
    temp = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, temp) if source else temp.write_text(text or "", encoding="utf-8")
    temp.replace(destination)

# Validates a path against existence and type constraints, returning an error string if any check fails.
def _check_path(path: str, *, must_exist=False, must_be_file=False) -> tuple[Path, str | None]:
    p = _resolve_path(path)
    if must_exist and not p.exists(): return p, f"ERROR: File not found: {p}"
    if must_be_file and not p.is_file(): return p, f"ERROR: Not a file: {p}"
    return p, None

# Lists files matching a glob pattern inside a directory, skipping ignored dirs like .git and venv.
async def list_files(
    directory: Annotated[str, "Directory to inspect. Use '.' for the project root."] = ".",
    pattern: Annotated[str, "Glob pattern e.g. '*.csv'. Use exact filename first when user names a specific file."] = "*",
    limit: Annotated[int, "Maximum number of files to return."] = DEFAULT_FILE_LIST_LIMIT,
) -> str:
    """List matching files so local datasets and documents can be discovered quickly."""
    base = _resolve_path(directory)
    if not base.exists(): return f"ERROR: Directory not found: {base}"
    if not base.is_dir(): return f"ERROR: Not a directory: {base}"
    inside_ignored = any(part in IGNORED_DIRS for part in base.relative_to(PROJECT_ROOT).parts) if base.is_relative_to(PROJECT_ROOT) else False
    matches = sorted(p for p in base.rglob(pattern) if p.is_file() and (inside_ignored or not any(part in IGNORED_DIRS for part in p.parts)))
    if not matches:
        return f"ERROR: File not found: {base / pattern}" if not any(c in pattern for c in "*?[") else f"No files matched '{pattern}' in {base}"
    result = [str(p) for p in matches[:limit]]
    if len(matches) > limit: result.append(f"... {len(matches) - limit} more files omitted")
    return "\n".join(result)

# Reads a text file and returns its content, truncated to a max character limit.
async def read_text_file(
    path: Annotated[str, "Absolute or project-relative path to a text file."],
    max_chars: Annotated[int, "Maximum characters to return."] = DEFAULT_TEXT_PREVIEW_CHARS,
) -> str:
    """Read a local text file and return a trimmed preview."""
    p, err = _check_path(path, must_be_file=True)
    if err: return err
    content = p.read_text(encoding="utf-8", errors="ignore")
    if len(content) > max_chars: content = content[:max_chars] + "\n... [truncated]"
    return f"Path: {p}\n\n{content}"

# Builds a summary string for a CSV file with shape, columns, dtypes, and optional stats.
def _summarize_csv(path: str, *, rows: int = 5, detailed: bool = False) -> str:
    p, err = _check_path(path, must_be_file=True)
    if err: return err
    df = pd.read_csv(p)
    lines = [f"Path: {p}", f"Rows: {len(df)}", f"Columns: {list(df.columns)}"]
    if not detailed:
        lines += ["Dtypes:", *[f"- {c}: {t}" for c, t in df.dtypes.items()], "", "Sample rows:", df.head(rows).to_string(index=False)]
        return "\n".join(lines)
    missing = df.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty: lines += ["Missing values:", *[f"- {c}: {n}" for c, n in missing.items()]]
    num_cols = df.select_dtypes(include="number").columns
    if len(num_cols):
        lines += ["Numeric summary:", *[f"- {c}: min={df[c].min()}, max={df[c].max()}, mean={df[c].mean():.2f}, median={df[c].median():.2f}" for c in num_cols]]
    cat_cols = df.select_dtypes(exclude="number").columns
    if len(cat_cols):
        lines += ["Categorical summary:", *[f"- {c}: {', '.join(f'{i}={v}' for i, v in df[c].value_counts().head(5).items())}" for c in cat_cols]]
    return "\n".join(lines)

# Returns a quick schema and sample row preview for a CSV file.
async def inspect_csv(
    path: Annotated[str, "Absolute or project-relative path to a CSV file."],
    rows: Annotated[int, "Sample rows to include."] = 5,
) -> str:
    """Inspect a CSV: shape, columns, dtypes, and sample rows."""
    return _summarize_csv(path, rows=rows)

# Returns a detailed analytical profile of a CSV including missing values and numeric/categorical stats.
async def analyze_csv(
    path: Annotated[str, "Absolute or project-relative path to a CSV file."],
) -> str:
    """Compute a compact analytical profile of a CSV."""
    return _summarize_csv(path, detailed=True)

# Writes text content to a file inside the active query folder, creating parent directories as needed.
async def write_text_file(
    path: Annotated[str, "Relative output path to create or overwrite."],
    content: Annotated[str, "Final text content. No placeholders or partial drafts."],
) -> str:
    """Write a final text file. Output goes to the active query folder inside .runtime/code/."""
    p = _resolve_write_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    _replace_file(p, text=content)
    return f"Wrote {len(content)} characters to {p}"

# Copies a file from anywhere in the project into the active query folder workspace.
async def copy_file_to_workspace(
    source_path: Annotated[str, "Absolute or project-relative path to source file."],
    output_path: Annotated[str, "Relative destination path."],
) -> str:
    """Copy an existing file into the active query folder."""
    src, err = _check_path(source_path, must_exist=True, must_be_file=True)
    if err: return err
    dst = _resolve_write_path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    _replace_file(dst, source=src)
    return f"Copied {src} to {dst}"

# Extracts line count, classes, and function names from a source file to inform analysis reports.
async def get_source_info(
    path: Annotated[str, "Absolute or project-relative path to a source file."],
) -> str:
    """Return line count and, for Python files, class and function names."""
    p, err = _check_path(path, must_exist=True, must_be_file=True)
    if err: return err
    source_text = p.read_text(encoding="utf-8", errors="ignore")
    info = [f"Path: {p}", f"Line count: {len(source_text.splitlines())}"]
    if p.suffix == ".py":
        classes = ', '.join(re.findall(r'^\s*class\s+([A-Za-z_]\w*)\s*[:(]', source_text, re.MULTILINE)) or "None"
        funcs   = ', '.join(re.findall(r'^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(', source_text, re.MULTILINE)) or "None"
        info += [f"Classes: {classes}", f"Functions: {funcs}"]
    return "\n".join(info)

# Instantiates and returns the FileAgent with all file tools registered and its system prompt configured.
def create_file_agent(model_client) -> AssistantAgent:
    return AssistantAgent(
        name="FileAgent",
        description="Accepts one plain-English task string. Handles local files, text analysis, CSV analysis, and workspace-safe file writing.",
        model_client=model_client,
        tools=[list_files, read_text_file, inspect_csv, analyze_csv,
               write_text_file, copy_file_to_workspace, get_source_info],
        system_message=(
            "You are the file specialist for a local AutoGen workflow. Tasks arrive as plain-English strings.\n"
            "TOOLS: discover files, read text, inspect/analyze CSVs, write output files.\n"
            "DO NOT: create/populate SQLite DBs, read .db files (binary), write helper scripts for DB work — delegate those to DatabaseAgent/CodeExecutorAgent.\n"
            "FILES: Use exact filename as pattern in list_files first. On ERROR, report it and stop — do not retry with a different path or broaden the search.\n"
            "READ-ONLY TASKS: If the user asked to verify, inspect, analyze, summarize, preview, count, or read a file, stay read-only. Do not write, copy, or create any file unless the user explicitly asked for an output artifact.\n"
            "REPORTS: Use analyze_csv for summary facts, inspect_csv for schema/samples. To write a source analysis report: call get_source_info first, then compose the full markdown and write it with write_text_file.\n"
            "PATHS: Never invent output filenames for read-only tasks. If a write task does not specify a filename, ask for or infer a sensible artifact name only when file creation was explicitly requested. Never write outside the project workspace.\n"
            "COPYING: If CodeExecutorAgent wrote files to .runtime/code, use copy_file_to_workspace to bring them into the workspace.\n"
            "ERRORS: Any tool response starting with 'ERROR:' — stop immediately, report it, do not call more tools.\n"
            "FINAL OUTPUT: Your visible result after tool use is the LAST tool result, so make the last tool call the one that returns the final file preview, final analysis, or write confirmation."
        ),
        reflect_on_tool_use=False,
        tool_call_summary_format="{result}",
        max_tool_iterations=6,
    )
