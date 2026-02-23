import os
import re
import sys

import yaml
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/model.yaml"))


def _load_gemini(config_path: str | None = None):
    cfg = yaml.safe_load(open(config_path or _CONFIG_PATH))
    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        raise EnvironmentError(f"Set the '{cfg['api_key_env']}' environment variable.")
    return genai.Client(api_key=api_key), cfg["model_name"]


class SQLGenerator:
    def __init__(self, config_path: str | None = None):
        self._client, self._model = _load_gemini(config_path)

    def _generate(self, prompt: str) -> str:
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        text = resp.text.strip()
        text = re.sub(r"^```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
        return re.sub(r"```$", "", text).strip()

    def is_safe_query(self, sql: str) -> bool:
        forbidden = [
            r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
            r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b", r"\bREVOKE\b",
            r"\bATTACH\b", r"\bDETACH\b", r"\bPRAGMA\b",
        ]
        for pattern in forbidden:
            if re.search(pattern, sql, re.IGNORECASE):
                return False
        return bool(re.search(r"^\s*(WITH\s+.*?SELECT\b|SELECT\b)", sql, re.IGNORECASE | re.DOTALL))

    def generate_sql(self, schema: str, user_query: str) -> str:
        prompt = f"""You are an expert SQLite developer.
Given the schema below, write a SQL query answering the user's question.

{schema}

Question: "{user_query}"

Return ONLY the raw SQL SELECT query. No markdown, no explanations.
All column/table names are lowercase with underscores.
"""
        sql = self._generate(prompt)
        print(f"Generated SQL:\n{sql}\n")
        if not self.is_safe_query(sql):
            raise ValueError(f"SECURITY ALERT: Unsafe SQL blocked.\n{sql}")
        return sql

    def fix_sql(self, schema: str, broken_sql: str, error: str) -> str:
        prompt = f"""Fix this SQLite query that produced an error.

Schema:
{schema}

Broken SQL:
{broken_sql}

Error: {error}

Return ONLY the corrected raw SQL query. No markdown, no explanations.
"""
        sql = self._generate(prompt)
        print(f"Corrected SQL:\n{sql}\n")
        if not self.is_safe_query(sql):
            raise ValueError(f"SECURITY ALERT: Corrected SQL still unsafe.\n{sql}")
        return sql