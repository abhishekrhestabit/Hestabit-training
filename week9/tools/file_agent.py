from __future__ import annotations
from collections import Counter
from html import escape
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
WORD_RE = re.compile(r"[A-Za-z0-9']+")
_active_query_folder: str | None = None

def set_query_folder(folder_name: str | None) -> None:
    global _active_query_folder
    _active_query_folder = folder_name
    if folder_name: (RUNTIME_CODE_DIR / folder_name).mkdir(parents=True, exist_ok=True)

def _resolve_write_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute(): return candidate.resolve()
    if _active_query_folder: return (RUNTIME_CODE_DIR / _active_query_folder / candidate).resolve()
    return (PROJECT_ROOT / candidate).resolve()

def _resolve_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()

def _replace_file(destination: Path, *, text: str | None = None, source: Path | None = None) -> None:
    temp = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, temp) if source else temp.write_text(text or "", encoding="utf-8")
    temp.replace(destination)

def _check_path(path: str, *, must_exist=False, must_be_file=False, write=False) -> tuple[Path, str | None]:
    p = _resolve_path(path)
    if write and not p.is_relative_to(PROJECT_ROOT): return p, f"ERROR: Refusing to write outside project workspace: {p}"
    if must_exist and not p.exists(): return p, f"ERROR: File not found: {p}"
    if must_be_file and not p.is_file(): return p, f"ERROR: Not a file: {p}"
    return p, None

def _word_counts(content: str) -> list[tuple[str, int]]:
    return sorted(Counter(w.lower() for w in WORD_RE.findall(content)).items(), key=lambda x: (-x[1], x[0]))

async def list_files(
    directory: Annotated[str, "Directory to inspect. Use '.' for the project root."] = ".",
    pattern: Annotated[str, "Glob pattern e.g. '*.csv'. Use exact filename first when user names a specific file."] = "*",
    limit: Annotated[int, "Maximum number of files to return."] = DEFAULT_FILE_LIST_LIMIT,
) -> str:
    """List matching files so local datasets and documents can be discovered quickly."""
    base, err = _check_path(directory)
    if not base.exists(): return f"ERROR: Directory not found: {base}"
    if not base.is_dir(): return f"ERROR: Not a directory: {base}"
    inside_ignored = any(part in IGNORED_DIRS for part in base.relative_to(PROJECT_ROOT).parts) if base.is_relative_to(PROJECT_ROOT) else False
    matches = sorted(p for p in base.rglob(pattern) if p.is_file() and (inside_ignored or not any(part in IGNORED_DIRS for part in p.parts)))
    if not matches:
        return f"ERROR: File not found: {base / pattern}" if not any(c in pattern for c in "*?[") else f"No files matched '{pattern}' in {base}"
    result = [str(p) for p in matches[:limit]]
    if len(matches) > limit: result.append(f"... {len(matches) - limit} more files omitted")
    return "\n".join(result)

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

async def inspect_csv(
    path: Annotated[str, "Absolute or project-relative path to a CSV file."],
    rows: Annotated[int, "Sample rows to include."] = 5,
) -> str:
    """Inspect a CSV: shape, columns, dtypes, and sample rows."""
    return _summarize_csv(path, rows=rows)

async def analyze_csv(
    path: Annotated[str, "Absolute or project-relative path to a CSV file."],
) -> str:
    """Compute a compact analytical profile of a CSV."""
    return _summarize_csv(path, detailed=True)

async def count_words_in_text_file(
    path: Annotated[str, "Absolute or project-relative path to a text file."],
) -> str:
    """Count word frequencies in a text file."""
    p, err = _check_path(path, must_be_file=True)
    if err: return err
    counts = _word_counts(p.read_text(encoding="utf-8", errors="ignore"))
    if not counts: return f"Path: {p}\nThe file is empty after tokenization."
    return f"Path: {p}\nUnique words: {len(counts)}\nWord counts:\n" + "\n".join(f"- {w}: {c}" for w, c in counts)

async def ensure_directory(
    path: Annotated[str, "Relative directory path to create if it does not already exist."],
) -> str:
    """Create a directory inside the active query folder."""
    p = _resolve_write_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"Ensured directory exists: {p}"

async def write_word_count_distribution_svg(
    path: Annotated[str, "Absolute or project-relative path to a text file."],
    output_path: Annotated[str, "Project-relative output path for the SVG file."],
    top_n: Annotated[int, "Number of most frequent words to plot."] = 15,
) -> str:
    """Create an SVG bar chart of the most frequent words in a text file."""
    src, err = _check_path(path, must_be_file=True)
    if err: return err
    dst = _resolve_write_path(output_path)
    counts = _word_counts(src.read_text(encoding="utf-8", errors="ignore"))[:max(1, top_n)]
    if not counts: return f"ERROR: No words found in {src}"
    max_count = max(c for _, c in counts)
    W, left, top, bh, gap = 960, 180, 48, 24, 12
    H = top + len(counts) * (bh + gap) + 40
    scale = W - left - 100
    bars = []
    for i, (word, count) in enumerate(counts):
        y = top + i * (bh + gap)
        bw = max(1, int(scale * count / max_count))
        bars += [
            f'<text x="16" y="{y+17}" font-family="monospace" font-size="14">{escape(word)}</text>',
            f'<rect x="{left}" y="{y}" width="{bw}" height="{bh}" rx="4" fill="#2563eb" />',
            f'<text x="{left+bw+8}" y="{y+17}" font-family="monospace" font-size="14">{count}</text>',
        ]
    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        '<text x="16" y="28" font-family="monospace" font-size="18">Word Count Distribution</text>',
        *bars, "</svg>",
    ])
    dst.parent.mkdir(parents=True, exist_ok=True)
    _replace_file(dst, text=svg + "\n")
    return f"Wrote word-count distribution SVG to {dst}"

async def write_text_file(
    path: Annotated[str, "Relative output path to create or overwrite."],
    content: Annotated[str, "Final text content. No placeholders or partial drafts."],
) -> str:
    """Write a final text file. Output goes to the active query folder inside .runtime/code/."""
    p = _resolve_write_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    _replace_file(p, text=content)
    return f"Wrote {len(content)} characters to {p}"

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

async def write_analysis_report(
    path: Annotated[str, "Relative path for the report file (.md or .txt)."],
    source_path: Annotated[str, "Path to the source file being analyzed."],
    report_markdown: Annotated[str, "Complete final markdown report to write."],
) -> str:
    """Write a markdown analysis report with an auto-generated source snapshot."""
    out = _resolve_write_path(path)
    src, err = _check_path(source_path, must_exist=True, must_be_file=True)
    if err: return err
    if not report_markdown.strip(): return "ERROR: Analysis report cannot be empty."
    source_text = src.read_text(encoding="utf-8", errors="ignore")
    classes_found, funcs_found = "None", "None"
    if src.suffix == ".py":
        classes_found = ', '.join(re.findall(r'^\s*class\s+([A-Za-z_]\w*)\s*[:(]', source_text, re.MULTILINE)) or "None"
        funcs_found = ', '.join(re.findall(r'^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(', source_text, re.MULTILINE)) or "None"
    snapshot = "\n".join([
        "## Source Snapshot", f"- Path: {src}",
        f"- Approximate line count: {len(source_text.splitlines())}",
        f"- Classes: {classes_found}", f"- Functions: {funcs_found}",
    ])
    content = report_markdown.strip()
    if "## Source Snapshot" not in content:
        if content.startswith("#"):
            heading, _, rest = content.partition("\n")
            content = "\n\n".join(p for p in [heading, snapshot, rest.lstrip()] if p)
        else:
            content = f"# Analysis Report\n\n{snapshot}\n\n{content}"
    content = content.rstrip() + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    _replace_file(out, text=content)
    return f"Wrote analysis report ({len(content)} characters) to {out}"

def create_file_agent(model_client) -> AssistantAgent:
    return AssistantAgent(
        name="FileAgent",
        description="Accepts one plain-English task string. Handles local files, directory creation, text analysis, CSV analysis, and workspace-safe file writing.",
        model_client=model_client,
        tools=[list_files, read_text_file, inspect_csv, analyze_csv, count_words_in_text_file,
               ensure_directory, write_word_count_distribution_svg, write_text_file,
               copy_file_to_workspace, write_analysis_report],
        system_message=(
            "You are the file specialist for a local AutoGen workflow. Tasks arrive as plain-English strings.\n"
            "TOOLS: discover files, read text, inspect/analyze CSVs, count words, create directories, create SVG graphs, write output files.\n"
            "DO NOT: create/populate SQLite DBs, read .db files (binary), write helper scripts for DB work — delegate those to DatabaseAgent/CodeExecutorAgent.\n"
            "FILES: Use exact filename as pattern in list_files first. On ERROR, report it and stop — do not retry with a different path or broaden the search.\n"
            "READ-ONLY TASKS: If the user asked to verify, inspect, analyze, summarize, preview, count, or read a file, stay read-only. Do not write, copy, or create any file unless the user explicitly asked for an output artifact.\n"
            "DIRECTORIES: If the task is to create a folder or scaffold a new project path, use ensure_directory before writing files into it.\n"
            "REPORTS: Use analyze_csv for summary facts, inspect_csv for schema/samples. Only use write_text_file or write_analysis_report when the task explicitly asks you to create a file.\n"
            "GRAPHS: Use count_words_in_text_file + write_word_count_distribution_svg. Default output name: word_count_distribution.svg.\n"
            "PATHS: Never invent output filenames for read-only tasks. If a write task does not specify a filename, ask for or infer a sensible artifact name only when file creation was explicitly requested. Never write outside the project workspace.\n"
            "COPYING: If CodeExecutorAgent wrote files to .runtime/code, use copy_file_to_workspace to bring them into the workspace.\n"
            "ERRORS: Any tool response starting with 'ERROR:' — stop immediately, report it, do not call more tools.\n"
            "FINAL OUTPUT: Your visible result after tool use is the LAST tool result, so make the last tool call the one that returns the final file preview, final analysis, or write confirmation."
        ),
        reflect_on_tool_use=False,
        tool_call_summary_format="{result}",
        max_tool_iterations=6,
    )
