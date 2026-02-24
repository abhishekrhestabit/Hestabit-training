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
        # Block anything that writes, modifies, or restructures the database.
        # Everything else (SELECT, WITH, EXPLAIN, EXPLAIN QUERY PLAN, …) is allowed.
        write_commands = [
            r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bREPLACE\b", r"\bUPSERT\b",
            r"\bCREATE\b", r"\bDROP\b",   r"\bALTER\b",  r"\bRENAME\b", r"\bTRUNCATE\b",
            r"\bATTACH\b", r"\bDETACH\b",
            r"\bGRANT\b",  r"\bREVOKE\b",
            r"\bVACUUM\b", r"\bREINDEX\b",
        ]
        for pattern in write_commands:
            if re.search(pattern, sql, re.IGNORECASE):
                return False
        return True

    def generate_sql(self, schema: str, user_query: str, broken_sql: str = None, error_msg: str = None) -> str:
        prompt = f"""You are an expert SQLite developer.
Given the schema below, write a SQL query answering the user's question.

{schema}

Question: "{user_query}"
"""
        # Dynamically append the error correction logic if needed
        if broken_sql and error_msg:
            prompt += f"\nCRITICAL ERROR: Your last query failed.\nBroken SQL: {broken_sql}\nError: {error_msg}\nFix it."

        prompt += "\nReturn ONLY the raw SQL SELECT query. No markdown, no explanations."
        
        sql = self._generate(prompt)
        print(f"Generated SQL:\n{sql}\n")
        
        if not self.is_safe_query(sql):
            raise ValueError(f"SECURITY ALERT: Unsafe SQL blocked.\n{sql}")
        return sql