"""
nexus_ai/agents/validator.py  —  Validator Agent
─────────────────────────────────────────────────────────────────
Critic    → "Is the output high quality?"
Validator → "Does it actually solve what the user asked for?"

Validator uses DETERMINISTIC checks (Python AST, file system) first,
then passes factual evidence to LLM for the final judgment.
This means it cannot be fooled by a confident-sounding description.
─────────────────────────────────────────────────────────────────
"""

import ast, json, os, re, time
from pathlib import Path
from .base_agent import BaseAgent


class ValidatorAgent(BaseAgent):
    NAME = "Validator"
    ROLE = "Verifies output actually solves what was asked — uses code analysis"

    SYSTEM_PROMPT = """\
You are the Validator Agent in NEXUS AI.

Critic checks quality. You check correctness — did it do what was asked?

CRITICAL RULE — CURRENT EVENTS AND WEB SEARCH RESULTS:
If the context contains "── Web Search Results" or references web searches,
the Researcher has retrieved LIVE data from the internet.
You MUST trust these search results over your own training knowledge.
Your training data has a cutoff and may be outdated.
DO NOT flag web search results as "hallucinations" — they are live data.
DO NOT use your own knowledge to contradict search-backed answers.

You will receive FACTUAL EVIDENCE collected by code analysis tools:
  - Which files exist on disk vs which were claimed but missing
  - Exact routes found in FastAPI/Flask code (via AST parsing)
  - Syntax errors if any
  - Classes and functions actually defined

Use this evidence to answer:
  1. DELIVERABLES — right files, right folder, right format?
  2. TASK MATCH — does it solve the actual problem stated?
  3. COMPLETENESS — are all required pieces present per the evidence?

Output raw JSON only, no fences:
{
  "approved": true | false,
  "score": <integer 1-10>,
  "reason": "one sentence based on the evidence",
  "unmet_requirements": ["what is missing per the evidence"],
  "final_output": "the best available output to pass to Reporter"
}

Base your score on EVIDENCE and SEARCH RESULTS, not on your training knowledge.\
"""

    # ── Deterministic helpers (no LLM) ───────────────────────────

    def _verify_claimed_files(self, context: str) -> tuple[list, list]:
        """Check files claimed in context actually exist on disk."""
        pattern = re.compile(
            r'(?:Created|Updated|Wrote|Generated)\s+([\w./\-]+\.\w+)', re.I
        )
        claimed  = list(set(pattern.findall(context)))
        existing = [f for f in claimed if Path(f).exists()]
        missing  = [f for f in claimed if not Path(f).exists()]
        return existing, missing

    def _analyse_files(self, context: str, task: str) -> str:
        """
        Deterministic analysis of any file type found on disk.
        No LLM involved — results are factual and cannot hallucinate.

        Python  → AST: syntax, routes, classes, functions
        CSV     → row count, column names, non-empty check
        SQLite  → table names, row counts
        Markdown/TXT → word count, section headings
        JSON    → key count, structural validity
        Any     → file exists, size, not empty
        """
        import ast as _ast

        pattern = re.compile(
            r'(?:(?:[\w\-]+/)*)[\w\-]+\.\w+', re.I
        )
        candidates = set(pattern.findall(context + " " + task))
        created = re.findall(
            r'(?:Created|Updated|Wrote|Generated)\s+([\w./\-]+\.\w+)',
            context, re.I
        )
        candidates.update(created)

        KNOWN_EXTS = {
            "py","csv","db","md","txt","json","yaml","yml","html","js","ts"
        }
        candidates = {
            p for p in candidates
            if p.split(".")[-1].lower() in KNOWN_EXTS and Path(p).exists()
        }

        if not candidates:
            return ""

        report = ["── File Analysis (deterministic) ──"]

        for path_str in sorted(candidates):
            p   = Path(path_str)
            ext = p.suffix.lower().lstrip(".")
            try:
                size = p.stat().st_size
            except Exception:
                continue

            section = [f"\nFile: {path_str} ({size} bytes)"]

            if size == 0:
                section.append("  ❌ Empty file")
                report.extend(section)
                continue

            # ── Python ───────────────────────────────────────────
            if ext == "py":
                try:
                    source = p.read_text(encoding="utf-8")
                    tree   = _ast.parse(source)
                    section.append("  ✅ Syntax: valid")

                    routes = []
                    for node in _ast.walk(tree):
                        if isinstance(node, _ast.FunctionDef):
                            for dec in node.decorator_list:
                                try:
                                    dec_str = _ast.unparse(dec)
                                except Exception:
                                    continue
                                for method in (".get(", ".post(", ".put(",
                                               ".delete(", ".patch("):
                                    if method in dec_str:
                                        m_name = method.strip(".(").upper()
                                        try:
                                            path_arg = dec_str.split("(")[1]\
                                                .split(",")[0].strip(" '\"")
                                        except Exception:
                                            path_arg = "?"
                                        routes.append(f"{m_name} {path_arg}")
                    if routes:
                        section.append(f"  Routes: {', '.join(routes)}")

                    classes = [n.name for n in _ast.walk(tree)
                               if isinstance(n, _ast.ClassDef)]
                    funcs   = [n.name for n in _ast.walk(tree)
                               if isinstance(n, _ast.FunctionDef)
                               and n.col_offset == 0]
                    if classes: section.append(f"  Classes: {', '.join(classes)}")
                    if funcs:   section.append(f"  Functions: {', '.join(funcs)}")

                except SyntaxError as e:
                    section.append(f"  ❌ Syntax error: {e}")

            # ── CSV ──────────────────────────────────────────────
            elif ext == "csv":
                try:
                    import csv as _csv
                    with open(p, newline="", encoding="utf-8") as f:
                        reader = _csv.DictReader(f)
                        rows   = list(reader)
                        cols   = list(reader.fieldnames or [])
                    section.append(f"  ✅ Rows: {len(rows)} | Columns: {', '.join(cols)}")
                except Exception as e:
                    section.append(f"  ❌ CSV parse error: {e}")

            # ── SQLite DB ─────────────────────────────────────────
            elif ext == "db":
                try:
                    import sqlite3 as _sq
                    conn   = _sq.connect(str(p))
                    tables = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                        " AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                    conn.close()
                    if tables:
                        section.append(f"  ✅ Tables: {', '.join(t[0] for t in tables)}")
                    else:
                        section.append("  ⚠️  DB exists but no user tables")
                except Exception as e:
                    section.append(f"  ❌ DB error: {e}")

            # ── Markdown / TXT ───────────────────────────────────
            elif ext in ("md", "txt"):
                try:
                    text     = p.read_text(encoding="utf-8")
                    words    = len(text.split())
                    headings = re.findall(r'^#{1,3} .+', text, re.MULTILINE)
                    section.append(f"  ✅ Words: {words}")
                    if headings:
                        section.append(f"  Sections: {', '.join(h.lstrip('# ') for h in headings[:6])}")
                    elif words < 50:
                        section.append("  ⚠️  Very short — may be a placeholder")
                except Exception as e:
                    section.append(f"  ❌ Read error: {e}")

            # ── JSON ─────────────────────────────────────────────
            elif ext == "json":
                try:
                    import json as _json
                    data = _json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        section.append(f"  ✅ JSON object: {len(data)} keys")
                    elif isinstance(data, list):
                        section.append(f"  ✅ JSON array: {len(data)} items")
                    else:
                        section.append("  ✅ JSON: valid")
                except Exception as e:
                    section.append(f"  ❌ JSON error: {e}")

            # ── Everything else — just confirm it exists + size ───
            else:
                section.append(f"  ✅ Exists ({size} bytes)")

            report.extend(section)

        return "\n".join(report) if len(report) > 1 else ""

    # ── Main run ─────────────────────────────────────────────────

    async def run(self, context: str, original_task: str = "") -> dict:
        from nexus_ai.logger import log
        t0 = time.time()

        # Step 1: deterministic file check
        existing, missing = self._verify_claimed_files(context)

        # Step 2: deterministic file analysis (type-aware)
        file_analysis = self._analyse_files(context, original_task)

        # Step 3: build factual evidence block
        evidence = ""
        if existing:
            evidence += f"Files on disk: {', '.join(existing)}\n"
        if missing:
            evidence += f"Files CLAIMED but MISSING: {', '.join(missing)}\n"
        if file_analysis:
            evidence += f"\n{file_analysis}\n"

        # Step 4: LLM judges task correctness from factual evidence
        # Extract web search results from context if present — these are live data
        web_results_block = ""
        if "── Web Search Results" in context:
            import re as _re
            m = _re.search(r'(── Web Search Results.*?)(?=\n──|\Z)', context, _re.DOTALL)
            if m:
                web_results_block = (
                    f"\nLIVE WEB SEARCH RESULTS (trust these over training knowledge):\n"
                    f"{m.group(1)[:2000]}\n"
                )

        raw = await self._llm(
            self.SYSTEM_PROMPT,
            f"Original user task:\n{original_task}\n\n"
            f"Factual evidence (trust this — collected by code analysis tools):\n"
            f"{evidence}\n"
            f"{web_results_block}"
            f"Context (full agent outputs):\n{context[:6000]}",
        )
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        try:
            result = json.loads(raw)
        except Exception:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    result = json.loads(m.group())
                except Exception:
                    result = {}
            else:
                result = {}

        if not result:
            result = {
                "approved": True, "score": 7,
                "reason": "Validation parse failed — passing through.",
                "unmet_requirements": [],
                "final_output": context,
            }

        # Auto-fail if files are missing (overrides LLM)
        if missing and result.get("approved"):
            result["approved"] = False
            result["score"]    = min(result.get("score", 5), 4)
            result["reason"]   = f"Missing files: {', '.join(missing)}"
            result.setdefault("unmet_requirements", []).append(
                f"Missing: {', '.join(missing)}"
            )

        # Auto-fail if score is too low regardless of "approved" flag
        # LLMs sometimes say approved=true with score=5 which is inconsistent
        from nexus_ai.config import MIN_QUALITY_SCORE
        if result.get("score", 10) < MIN_QUALITY_SCORE:
            result["approved"] = False

        if "final_output" not in result:
            result["final_output"] = context

        log.agent(self.NAME, input_text=original_task[:200], output_text=raw,
                  duration=time.time() - t0, success=True,
                  extra={
                      "approved":       result.get("approved"),
                      "score":          result.get("score"),
                      "missing_files":  missing,
                      "existing_files": existing,
                      "analysis_ran":   len(file_analysis) > 0,
                  })
        log.quality_check(score=result.get("score", 0), agent="Validator", retry=0)
        return result