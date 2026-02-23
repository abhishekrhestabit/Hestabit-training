import os
import re
import sqlite3

import pandas as pd

def _sanitize_name(name: str) -> str:
    """Turn 'First Name' → 'first_name', 'Customer Id' → 'customer_id'."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)   # non-alphanumeric → _
    name = name.strip("_")
    return name


def _csv_table_name(filename: str) -> str:
    """'customers-1000.csv' → 'customers'  (strip trailing numbers/dashes)."""
    base = os.path.splitext(os.path.basename(filename))[0]
    # Remove trailing -NNN or _NNN suffixes  (e.g. customers-1000 → customers)
    base = re.sub(r"[-_]\d+$", "", base)
    return _sanitize_name(base)


def load_csvs_to_db(csv_dir: str, db_path: str) -> list[str]:
  
    csv_files = [f for f in os.listdir(csv_dir) if f.lower().endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {csv_dir}")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    table_names = []

    for filename in csv_files:
        filepath = os.path.join(csv_dir, filename)
        table_name = _csv_table_name(filename)

        df = pd.read_csv(filepath)

        # Sanitise column names
        df.columns = [_sanitize_name(c) for c in df.columns]

        # Drop duplicate column names that can appear after sanitisation
        df = df.loc[:, ~df.columns.duplicated()]

        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"  ✔ Loaded '{filename}' → table '{table_name}' ({len(df)} rows)")
        table_names.append(table_name)

    conn.close()
    return table_names

class SchemaLoader:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_schema(self, sample_rows: int = 3) -> str:
  
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = cursor.fetchall()

            if not tables:
                return "No tables found in the database."

            parts = ["Database Schema:\n"]
            for table_name, ddl in tables:
                if ddl:
                    parts.append(f"-- Table: {table_name}")
                    parts.append(f"{ddl};\n")

                    # Sample rows
                    try:
                        cursor.execute(
                            f"SELECT * FROM \"{table_name}\" LIMIT {sample_rows};"
                        )
                        rows = cursor.fetchall()
                        col_names = [d[0] for d in cursor.description]
                        if rows:
                            parts.append(f"-- Sample rows from '{table_name}':")
                            parts.append("-- " + " | ".join(col_names))
                            for row in rows:
                                parts.append("-- " + " | ".join(str(v) for v in row))
                        parts.append("")
                    except sqlite3.Error:
                        pass  # non-fatal – skip samples for this table

            return "\n".join(parts).strip()

        except sqlite3.Error as e:
            return f"Error loading schema: {e}"
        finally:
            if conn:
                conn.close()