"""
tools/file_agent.py
─────────────────────────────────────────────────────────────────
File I/O utilities for the pipeline.

Used directly by day3_pipeline.py.

Public API:
    read_txt(file_path)               → str
    read_csv(file_path)               → dict  {rows, columns, count, stats}
    read_json(file_path)              → dict  {data}
    write_txt(file_path, text)        → str   confirmation
    write_csv(file_path, rows)        → str   confirmation
    read_file(file_path)              → str   smart display string (for answer gen)
    create_sample_csv(file_path)      → str   demo data
─────────────────────────────────────────────────────────────────
"""

import csv
import json
import statistics
from pathlib import Path


# ─────────────────────────────────────────────────────────────────
#  READ functions — each returns structured data, not display text
# ─────────────────────────────────────────────────────────────────

def read_txt(file_path: str) -> str:
    """
    Read a plain text file (.txt, .md, .log, .py, .yaml, etc.)
    Returns the raw text content, or an error string starting with ❌.
    """
    path = Path(file_path)
    if not path.exists():
        return f"❌ File not found: {file_path}"
    return path.read_text(encoding="utf-8")


def read_csv(file_path: str) -> dict:
    """
    Parse a CSV file into structured data.

    Returns:
        {
            "success":  bool,
            "rows":     list[dict],   one dict per row, keys = column names
            "columns":  list[str],
            "count":    int,
            "stats":    dict,         per-column stats (min/max/mean or unique)
            "error":    str | None,
        }

    Use this when you need the actual data (to pass to code, or insert to DB).
    Use read_file() when you just need a display string for the final answer.
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "rows": [], "columns": [],
                "count": 0, "stats": {}, "error": f"File not found: {file_path}"}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader  = csv.DictReader(f)
            rows    = list(reader)
            columns = list(reader.fieldnames or [])

        stats = {}
        for col in columns:
            values = [r[col] for r in rows if r.get(col, "").strip() != ""]
            try:
                nums = [float(v) for v in values]
                stats[col] = {
                    "type":  "numeric",
                    "count": len(nums),
                    "min":   min(nums),
                    "max":   max(nums),
                    "mean":  round(statistics.mean(nums), 2),
                    "stdev": round(statistics.stdev(nums), 2) if len(nums) > 1 else 0.0,
                }
            except ValueError:
                unique = list(dict.fromkeys(values))
                stats[col] = {
                    "type":   "text",
                    "count":  len(values),
                    "unique": len(unique),
                    "values": unique[:10],
                }

        return {"success": True, "rows": rows, "columns": columns,
                "count": len(rows), "stats": stats, "error": None}
    except Exception as e:
        return {"success": False, "rows": [], "columns": [],
                "count": 0, "stats": {}, "error": str(e)}


def read_json(file_path: str) -> dict:
    """
    Parse a JSON file.

    Returns:
        {"success": bool, "data": any, "error": str | None}
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "data": None,
                "error": f"File not found: {file_path}"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"success": True, "data": data, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─────────────────────────────────────────────────────────────────
#  WRITE functions — each validates its input before writing
# ─────────────────────────────────────────────────────────────────

def write_txt(file_path: str, text: str, append: bool = False) -> str:
    """
    Write plain text to a file. Creates parent directories automatically.
    Set append=True to add to an existing file.
    Returns a ✅ confirmation string.
    """
    path   = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode   = "a" if append else "w"
    action = "Appended to" if append else "Written"
    with open(path, mode, encoding="utf-8") as f:
        f.write(text)
    return f"✅ {action}: {file_path} ({len(text)} chars)"


def write_csv(file_path: str, rows: list) -> str:
    """
    Write rows to a CSV file using csv.DictWriter.
    Accepts:
      - list of dicts:  [{"name": "Jupiter", "diameter_km": 139820}, ...]
      - list of lists:  [["Jupiter", 139820, 95], ...]  with first row as headers
      - list of lists without headers — columns named col_0, col_1, ...

    Guarantees proper CSV escaping via DictWriter regardless of input format.
    Returns a ✅ confirmation string, or ❌ on error.
    """
    if not rows:
        return "❌ write_csv: no rows provided."

    try:
        # ── Normalise to list[dict] ───────────────────────────────
        if isinstance(rows[0], dict):
            dict_rows = rows

        elif isinstance(rows[0], (list, tuple)):
            # If first row looks like headers (all strings), use it as header
            if all(isinstance(v, str) for v in rows[0]):
                headers   = [str(h) for h in rows[0]]
                dict_rows = [dict(zip(headers, r)) for r in rows[1:]]
            else:
                # No header row — auto-name columns
                n_cols    = len(rows[0])
                headers   = [f"col_{i}" for i in range(n_cols)]
                dict_rows = [dict(zip(headers, r)) for r in rows]

        else:
            return f"❌ write_csv: unrecognised row format: {type(rows[0])}"

        if not dict_rows:
            return "❌ write_csv: no data rows after normalisation."

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=dict_rows[0].keys())
            writer.writeheader()
            writer.writerows(dict_rows)

        return (f"✅ CSV written: {file_path} "
                f"({len(dict_rows)} rows, {len(dict_rows[0])} columns)")

    except Exception as e:
        return f"❌ write_csv failed: {e}"


# ─────────────────────────────────────────────────────────────────
#  DISPLAY helper — used by the answer generator and CLI output
# ─────────────────────────────────────────────────────────────────

def read_file(file_path: str) -> str:
    """
    Smart display reader — returns a human-readable string of the file.
    Used by the pipeline's answer generator and CLI info output.

    For structured access to CSV data, use read_csv() instead.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".csv":
        result = read_csv(file_path)
        if not result["success"]:
            return f"❌ {result['error']}"

        rows, columns = result["rows"], result["columns"]
        lines = [
            f"✅ CSV: {file_path}  ({result['count']} rows × {len(columns)} cols)",
            f"   Columns: {', '.join(columns)}", "",
            "── Rows ──",
        ]
        for i, r in enumerate(rows, 1):
            lines.append(f"  {i:>3}. " +
                         " | ".join(f"{k}={v}" for k, v in r.items()))
        lines.append("")
        lines.append("── Statistics ──")
        for col, s in result["stats"].items():
            if s["type"] == "numeric":
                lines.append(
                    f"  [{col}] numeric  min={s['min']}  max={s['max']}"
                    f"  mean={s['mean']}  stdev={s['stdev']}"
                )
            else:
                lines.append(
                    f"  [{col}] text  unique={s['unique']}  values={s['values'][:5]}"
                )
        return "\n".join(lines)

    elif suffix == ".json":
        result = read_json(file_path)
        if not result["success"]:
            return f"❌ {result['error']}"
        return (f"✅ JSON: {file_path}\n\n"
                f"{json.dumps(result['data'], indent=2)}")

    else:
        content = read_txt(file_path)
        if content.startswith("❌"):
            return content
        lines_n = content.count("\n") + 1
        return f"✅ Text: {file_path}  ({lines_n} lines)\n\n{content}"


# ─────────────────────────────────────────────────────────────────
#  Demo data
# ─────────────────────────────────────────────────────────────────

def create_sample_csv(file_path: str = "data/sales.csv") -> str:
    """Create sample sales data. Idempotent."""
    rows = [
        {"product": "Widget A", "region": "North", "amount": "15000", "units": "300", "month": "Jan"},
        {"product": "Widget B", "region": "South", "amount": "22000", "units": "440", "month": "Jan"},
        {"product": "Widget A", "region": "East",  "amount": "18000", "units": "360", "month": "Feb"},
        {"product": "Widget C", "region": "West",  "amount": "9500",  "units": "190", "month": "Feb"},
        {"product": "Widget B", "region": "North", "amount": "31000", "units": "620", "month": "Mar"},
        {"product": "Widget A", "region": "South", "amount": "27000", "units": "540", "month": "Mar"},
        {"product": "Widget C", "region": "East",  "amount": "12000", "units": "240", "month": "Apr"},
        {"product": "Widget B", "region": "West",  "amount": "19500", "units": "390", "month": "Apr"},
        {"product": "Widget A", "region": "North", "amount": "33000", "units": "660", "month": "May"},
        {"product": "Widget C", "region": "South", "amount": "8500",  "units": "170", "month": "May"},
    ]
    return write_csv(file_path, rows)