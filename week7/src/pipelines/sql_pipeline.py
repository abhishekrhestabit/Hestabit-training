import os
import sys
import sqlite3

import yaml
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.utils.schema_loader import SchemaLoader, load_csvs_to_db
from src.generator.sql_generator import SQLGenerator

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR     = os.path.join(BASE_DIR, "data", "sql")
_CONFIG_PATH = os.path.join(BASE_DIR, "config", "model.yaml")

class SQLQAPipeline:
    def __init__(self, csv_dir: str = CSV_DIR, config_path: str | None = None):
        print("Loading CSVs into in-memory SQLite...")
        self.conn = load_csvs_to_db(csv_dir)
        self.conn.row_factory = sqlite3.Row

        self.schema_loader = SchemaLoader(self.conn)
        self.sql_generator = SQLGenerator(config_path=config_path)

        cfg = yaml.safe_load(open(config_path or _CONFIG_PATH))
        api_key = os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            raise EnvironmentError(f"Set the '{cfg['api_key_env']}' environment variable.")
        self._client = genai.Client(api_key=api_key)
        self._model  = cfg["model_name"]
    def execute_query(self, sql: str):
        # Let the error raise naturally instead of returning a string
        cursor = self.conn.cursor()
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

    def summarize_results(self, user_query: str, sql: str, results: list) -> str:
        if not results:
            return "The database returned no results for this query."
        prompt = f"""User asked: "{user_query}"

SQL executed:
{sql}

Results (up to 50 rows):
{results[:50]}

Answer the user's question directly using the data above.
If the results are a list of records, include the actual names/values — do not just summarise counts.
Do not explain the SQL.
"""
        return self._client.models.generate_content(model=self._model, contents=prompt).text.strip()

    def run(self, user_query: str, display_query: str = "") -> str:
        label = display_query or user_query
        print(f"\nQuery: '{label}'")
        print("-" * 60)

        schema = self.schema_loader.get_schema()

        try:
            sql = self.sql_generator.generate_sql(schema, user_query)
        except ValueError as e:
            return str(e)

        results = self.execute_query(sql)
        print(f"Results (first 3): {results[:3]}\n")

        if isinstance(results, str) and results.startswith("Database Execution Error"):
            print("Execution failed. Retrying with auto-correction...")
            try:
                sql = self.sql_generator.generate_sql(schema, user_query, broken_sql=sql, error_msg=results)
                results = self.execute_query(sql)
                if isinstance(results, str):
                    return f"Query failed after correction:\n{results}", sql, []
            except ValueError as e:
                return str(e), sql, []

        return self.summarize_results(user_query, sql, results), sql, results


if __name__ == "__main__":
    pipeline = SQLQAPipeline()

    queries = [
        "How many customers are there in total?",
        "Return the customers whose name start with a",
        "Delete the customers subscribed in 2021?",
    ]

    for q in queries:
        answer, sql, results = pipeline.run(q)
        print("-" * 60)
        print(f"SQL:\n{sql}")
        print(f"Results (first 3): {results[:3]}")
        print(f"Answer:\n{answer}")
        print("=" * 60)
