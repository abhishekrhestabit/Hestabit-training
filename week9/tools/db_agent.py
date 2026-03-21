"""
tools/db_agent.py
─────────────────────────────────────────────────────────────────
SQLite database utilities for the pipeline.

Used directly by day3_pipeline.py — not via AutoGen agents.

Public API (what the pipeline calls):
    inspect_schema(db_path)           → str
    query_database(sql, db_path)      → str
    create_sample_sales_db(db_path)   → str  (demo data setup)
─────────────────────────────────────────────────────────────────
"""

import sqlite3
from pathlib import Path


# ─────────────────────────────────────────
#  Default DB path
# ─────────────────────────────────────────

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "agent_store.db"


# ─────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────

def _connect(db_path: str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _execute_sql(query: str, params: tuple = (),
                 db_path: str | None = None) -> dict:
    """
    Run any SQL statement.
    Returns {"success": bool, "rows": [...], "rowcount": int, "error": str|None}
    """
    conn = None
    try:
        conn = _connect(db_path)
        cur  = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        if query.strip().upper().startswith("SELECT"):
            rows = [dict(r) for r in cur.fetchall()]
            return {"success": True, "rows": rows,
                    "rowcount": len(rows), "error": None}
        return {"success": True, "rows": [],
                "rowcount": cur.rowcount, "error": None}
    except Exception as e:
        return {"success": False, "rows": [], "rowcount": 0, "error": str(e)}
    finally:
        if conn:
            conn.close()


# ─────────────────────────────────────────
#  Public API — called by the pipeline
# ─────────────────────────────────────────

def inspect_schema(db_path: str | None = None) -> str:
    """
    Return a detailed schema of all user tables: columns, types, and sample rows.
    Skips internal SQLite tables (sqlite_*).
    The SQL generator uses this to write accurate queries.
    """
    tables = _execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        db_path=db_path,
    )
    if not tables["success"]:
        return f"❌ Schema error: {tables['error']}"
    if not tables["rows"]:
        return "ℹ️ Database is empty (no user tables found)."

    lines = ["DATABASE SCHEMA", "=" * 40]
    for row in tables["rows"]:
        table   = row["name"]
        cols    = _execute_sql(f"PRAGMA table_info({table})", db_path=db_path)
        count   = _execute_sql(f"SELECT COUNT(*) as n FROM {table}", db_path=db_path)
        sample  = _execute_sql(f"SELECT * FROM {table} LIMIT 3", db_path=db_path)

        n_rows = count["rows"][0]["n"] if count["rows"] else "?"
        lines.append(f"\nTable: {table}  ({n_rows} rows total)")
        lines.append("Columns:")
        for col in cols["rows"]:
            pk  = " PRIMARY KEY" if col.get("pk") else ""
            lines.append(f"  {col['name']}  {col['type']}{pk}")

        if sample["rows"]:
            lines.append("Sample rows:")
            for r in sample["rows"]:
                lines.append("  " + ", ".join(f"{k}={v}" for k, v in r.items()))

    lines.append("\n" + "=" * 40)
    return "\n".join(lines)


def query_database(sql: str, db_path: str | None = None) -> str:
    """
    Execute a SQL query and return results as a formatted string.

    For SELECT: returns column headers + all rows.
    For INSERT/UPDATE/DELETE: returns rows affected count.
    Returns an error string starting with ❌ on failure.
    """
    result = _execute_sql(sql, db_path=db_path)
    if not result["success"]:
        return f"❌ SQL Error: {result['error']}"

    if result["rows"]:
        header   = " | ".join(result["rows"][0].keys())
        sep      = "─" * len(header)
        rows_str = "\n".join(
            " | ".join(str(v) for v in r.values())
            for r in result["rows"]
        )
        return (
            f"✅ Query OK — {result['rowcount']} row(s)\n\n"
            f"{header}\n{sep}\n{rows_str}"
        )
    return f"✅ Query OK — {result['rowcount']} row(s) affected."


# ─────────────────────────────────────────
#  Demo data helper (called from pipeline setup)
# ─────────────────────────────────────────

def create_sample_sales_db(db_path: str | None = None) -> str:
    """Create a sample sales.db for demos. Idempotent."""
    _execute_sql("""
        CREATE TABLE IF NOT EXISTS sales (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT    NOT NULL,
            region  TEXT    NOT NULL,
            amount  REAL    NOT NULL,
            units   INTEGER NOT NULL,
            month   TEXT    NOT NULL
        )
    """, db_path=db_path)

    rows = [
        ("Widget A", "North", 15000, 300, "Jan"),
        ("Widget B", "South", 22000, 440, "Jan"),
        ("Widget A", "East",  18000, 360, "Feb"),
        ("Widget C", "West",  9500,  190, "Feb"),
        ("Widget B", "North", 31000, 620, "Mar"),
        ("Widget A", "South", 27000, 540, "Mar"),
        ("Widget C", "East",  12000, 240, "Apr"),
        ("Widget B", "West",  19500, 390, "Apr"),
        ("Widget A", "North", 33000, 660, "May"),
        ("Widget C", "South", 8500,  170, "May"),
    ]
    conn = None
    try:
        conn = _connect(db_path)
        conn.executemany(
            "INSERT OR IGNORE INTO sales (product,region,amount,units,month) "
            "VALUES (?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        if conn:
            conn.close()

    target = db_path or str(DEFAULT_DB)
    return f"✅ Sample sales DB ready: {target} ({len(rows)} rows)"