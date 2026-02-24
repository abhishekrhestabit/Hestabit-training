import os
import sqlite3
import re
import pandas as pd


def _mask(value: str) -> str:
    return " ".join(w[0] + "*" * (len(w) - 1) if len(w) > 1 else w for w in str(value).split())


def load_csvs_to_db(csv_dir: str) -> sqlite3.Connection:
    csv_files = [f for f in os.listdir(csv_dir) if f.lower().endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {csv_dir}")

    conn = sqlite3.connect(":memory:")
    for filename in csv_files:
        df = pd.read_csv(os.path.join(csv_dir, filename))
        df.columns = [re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_") for c in df.columns]
        table = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(filename)[0].strip().lower()).strip("_")
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"  Loaded '{filename}' -> table '{table}' ({len(df)} rows)")

    return conn


class SchemaLoader:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_schema(self, sample_rows: int = 1) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        if not tables:
            return "No tables found."

        parts = ["Database Schema:\n"]
        for table_name, ddl in tables:
            if ddl:
                parts.append(f"-- Table: {table_name}\n{ddl};\n")
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT {sample_rows};')
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                if rows:
                    parts.append("-- Sample rows: " + " | ".join(cols))
                    parts.extend("-- " + " | ".join(_mask(v) for v in row) for row in rows)
                parts.append("")
        return "\n".join(parts).strip()