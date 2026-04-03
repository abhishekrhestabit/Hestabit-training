from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote
from autogen_agentchat.agents import AssistantAgent
from typing_extensions import Annotated

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_CODE_DIR = PROJECT_ROOT / ".runtime" / "code"
READ_ONLY_PREFIXES = ("select", "with", "pragma", "explain")
WRITE_PREFIXES = ("insert", "update", "delete", "replace", "create", "alter")


def _resolve_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if str(candidate).startswith("/workspace/"):
        rel = str(candidate)[len("/workspace/"):]
        return (RUNTIME_CODE_DIR / rel).resolve()
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{quote(str(db_path))}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _validate_read_only_query(query: str) -> str | None:
    statement = query.strip().rstrip(";")
    if not statement:
        return "Query cannot be empty."
    if not statement.lower().startswith(READ_ONLY_PREFIXES):
        return "Only read-only SQL is allowed. Use SELECT, WITH, PRAGMA, or EXPLAIN."
    return None


async def list_sqlite_tables(
    db_path: Annotated[str, "Absolute path or project-relative path to a SQLite database file."],
) -> str:
    """List all user tables in a SQLite database."""
    path = _resolve_path(db_path)
    if not path.exists():
        return f"Database not found: {path}"

    with _connect_read_only(path) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        return f"No user tables found in {path}"
    return f"Database: {path}\nTables:\n" + "\n".join(f"- {table}" for table in tables)


async def describe_sqlite_table(
    db_path: Annotated[str, "Absolute path or project-relative path to a SQLite database file."],
    table_name: Annotated[str, "The table name to describe."],
) -> str:
    """Describe the columns of a SQLite table."""
    path = _resolve_path(db_path)
    if not path.exists():
        return f"Database not found: {path}"

    safe_table = table_name.replace('"', '""')
    with _connect_read_only(path) as connection:
        cursor = connection.execute(f'PRAGMA table_info("{safe_table}")')
        rows = cursor.fetchall()

    if not rows:
        return f"Table '{table_name}' was not found in {path}"

    rendered = [
        f"- {row[1]} | type={row[2] or 'UNKNOWN'} | not_null={bool(row[3])} | pk={bool(row[5])}"
        for row in rows
    ]
    return f"Database: {path}\nTable: {table_name}\nColumns:\n" + "\n".join(rendered)


async def query_sqlite(
    db_path: Annotated[str, "Absolute path or project-relative path to a SQLite database file."],
    query: Annotated[str, "A read-only SQL query."],
    limit: Annotated[int, "Maximum number of rows to return."] = 100,
) -> str:
    """Run a read-only SQL query against a SQLite database and return a JSON preview."""
    path = _resolve_path(db_path)
    if not path.exists():
        return f"Database not found: {path}"

    error = _validate_read_only_query(query)
    if error:
        return error

    with _connect_read_only(path) as connection:
        cursor = connection.execute(query)
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(limit)

    records = [dict(zip(columns, row)) for row in rows]
    return (
        f"Database: {path}\n"
        f"Returned rows: {len(records)} (showing up to {limit})\n"
        f"Columns: {columns}\n"
        f"Rows:\n{json.dumps(records, indent=2, default=str)}"
    )


async def execute_sqlite(
    db_path: Annotated[str, "Absolute path or project-relative path to a SQLite database file."],
    query: Annotated[str, "A write SQL statement (INSERT, UPDATE, DELETE, CREATE, ALTER, REPLACE)."],
) -> str:
    """Execute a write SQL statement against a SQLite database."""
    path = _resolve_path(db_path)
    if not path.exists():
        return f"Database not found: {path}"

    statement = query.strip().rstrip(";")
    if not statement:
        return "Query cannot be empty."
    if statement.lower().startswith(READ_ONLY_PREFIXES):
        return "Use query_sqlite for read-only queries. This tool is for write operations (INSERT, UPDATE, DELETE)."
    if not statement.lower().startswith(WRITE_PREFIXES):
        return f"Unsupported operation. Allowed: INSERT, UPDATE, DELETE, REPLACE, CREATE, ALTER."

    try:
        with sqlite3.connect(str(path)) as conn:
            cursor = conn.execute(query)
            conn.commit()
            return f"Database: {path}\nExecuted successfully. Rows affected: {cursor.rowcount}"
    except sqlite3.Error as e:
        return f"Database: {path}\nSQL error: {e}"


def create_db_agent(model_client) -> AssistantAgent:
    return AssistantAgent(
        name="DatabaseAgent",
        description="Accepts one plain-English task string. Handles SQLite schema inspection, SQL queries, and write operations (INSERT, UPDATE, DELETE).",
        model_client=model_client,
        tools=[list_sqlite_tables, describe_sqlite_table, query_sqlite, execute_sqlite],
        system_message=(
            "You are the database specialist for a local AutoGen workflow. "
            "You are called through AgentTool, so the incoming task is always a single plain-English string. "
            "Use your tools to inspect SQLite databases, run read-only SQL queries, and execute write operations. "
            "Prefer schema inspection before querying. "
            "Use query_sqlite for SELECT or any read-only queries. Use execute_sqlite for INSERT, UPDATE, DELETE, CREATE, ALTER, or other write operations. "
            "If the task does not specify a database filename, respond immediately with: 'No database file was specified. Please include the database filename (e.g. user.db) in your request.' Do NOT guess or search for a database path. "
            "Your visible result after tool use is the LAST tool result, so make the last tool call the one that returns the actual schema details or query answer."
        ),
        reflect_on_tool_use=False,
        tool_call_summary_format="{result}",
        max_tool_iterations=6,
    )
