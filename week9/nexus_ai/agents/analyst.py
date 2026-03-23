"""
nexus_ai/agents/analyst.py  —  Analyst Agent
Data analysis using Day 3 file and DB tools.
"""

import time
from .base_agent import BaseAgent


class AnalystAgent(BaseAgent):
    NAME = "Analyst"
    ROLE = "Analyses data from files, CSVs, and databases"
    SYSTEM_PROMPT = """\
You are the Analyst Agent in NEXUS AI.

You analyse data and extract insights from files, CSVs, and databases.

RULES:
  - Identify patterns, trends, and anomalies
  - Provide specific numbers and statistics, not vague statements
  - Structure findings: Overview → Key Findings → Recommendations
  - If data shows something unexpected, flag it explicitly\
"""

    async def run(self, instruction: str, context: str = "",
                  file_path: str | None = None,
                  db_path: str | None = None) -> str:
        from nexus_ai.logger import log
        t0 = time.time()

        data_context = context

        # Read file if provided
        if file_path:
            try:
                from tools.file_agent import read_file, read_csv
                if file_path.endswith(".csv"):
                    result = read_csv(file_path)
                    if result["success"]:
                        data_context += f"\n\n── CSV Data: {file_path} ──\n"
                        data_context += f"{result['count']} rows × {len(result['columns'])} cols\n"
                        data_context += f"Columns: {', '.join(result['columns'])}\n"
                        for col, s in result["stats"].items():
                            data_context += f"  {col}: {s}\n"
                else:
                    data_context += f"\n\n── File: {file_path} ──\n{read_file(file_path)}"
            except Exception as e:
                data_context += f"\n[Could not read {file_path}: {e}]"

        # Query DB if provided
        if db_path:
            try:
                from tools.db_agent import inspect_schema, query_database
                schema = inspect_schema(db_path)
                data_context += f"\n\n── DB Schema: {db_path} ──\n{schema}"
            except Exception as e:
                data_context += f"\n[Could not inspect {db_path}: {e}]"

        result = await self._llm(
            self.SYSTEM_PROMPT,
            f"Analysis task:\n{instruction}\n\nData:\n{data_context}",
        )
        log.agent(self.NAME, input_text=instruction, output_text=result,
                  duration=time.time() - t0, success=True)
        return result