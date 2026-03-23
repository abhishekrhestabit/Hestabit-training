"""
nexus_ai/orchestrator.py
─────────────────────────────────────────────────────────────────
NEXUS AI Orchestrator

Flow:
  User Task
      ↓
  Planner     → execution plan (which agents, which order)
      ↓
  Agents run in planned order, each receiving previous outputs
      ↓
  Critic      → quality score + gaps  (if in plan)
      ↓ score < MIN_QUALITY_SCORE
  Optimizer   → improved output
      ↓
  Critic      → second review (max MAX_QUALITY_RETRIES cycles)
      ↓
  Validator   → final approval
      ↓
  Reporter    → final answer
─────────────────────────────────────────────────────────────────
"""

import time, re, json
from typing import AsyncGenerator

from nexus_ai.config   import MIN_QUALITY_SCORE, MAX_QUALITY_RETRIES
from nexus_ai.logger   import log
from nexus_ai.agents   import (
    PlannerAgent, ResearcherAgent, CoderAgent, AnalystAgent,
    CriticAgent, OptimizerAgent, ValidatorAgent, ReporterAgent,
)

# ── Day 4 memory (optional — graceful fallback if not available) ──
try:
    from memory.session_memory import SessionMemory
    from memory.vector_store   import VectorStore
    from memory.long_term      import LongTermMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    log.warn("Memory modules not found — running without memory")


def _is_simple(task: str) -> bool:
    """
    Classify whether a task needs the full multi-agent pipeline
    or can be answered with a single direct LLM call.

    Order of checks (important):
      1. Complex signals first — if ANY task keyword found, always pipeline
      2. Simple patterns — greetings, conversational, introductions
      3. Length fallback — very short with no task words
    """
    t = task.strip().lower()

    # ── 1. Complex signals — checked FIRST, override everything ──
    # If the message contains ANY of these, always use the pipeline
    # regardless of how the sentence starts ("Ok generate...", "Sure, build...")
    COMPLEX_SIGNALS = [
        "research", "analyse", "analyze", "analysis", "generate", "create",
        "build", "design", "implement", "write a", "write the", "code",
        "script", "api", "database", "csv", "file", "report", "compare",
        "explain how", "plan a", "plan the", "strategy", "architecture",
        "pipeline", "deploy", "summarize", "summarise", "read", "query",
        "search for", "find the", "calculate", "compute", "save", "store",
        "export", "dump", "put this", "write this", "how to", "how do",
        "how does", "what is the", "what are the", "tell me how",
        "give me a", "show me how", "help me", "i need a", "i need you to",
        "i want a", "i want you to", "can you create", "can you build",
        "can you write", "can you generate", "can you make",
    ]
    for signal in COMPLEX_SIGNALS:
        if signal in t:
            return False

    # ── 2. Simple patterns — only if no complex signals found ─────
    SIMPLE_PATTERNS = [
        r'^(hi|hello|hey|howdy|sup|yo)\b',
        r'^(thanks|thank you|thx|ty|ok|okay|got it|noted|sure|cool|great)\b',
        r'^(bye|goodbye|see you|cya)\b',
        r'^my name is\b',
        r'^i am\b',
        r'^i\'m\b',
        r'^do you remember\b',
        r'^what did we\b',
        r'^what is my\b',
        r'^who am i\b',
        r'^how are you\b',
        r'^what can you do\b',
        r'^tell me about yourself\b',
        r'^nice\b',
        r'^sounds good\b',
        r'^got it\b',
        r'^perfect\b',
        r'^awesome\b',
    ]
    for pattern in SIMPLE_PATTERNS:
        if re.match(pattern, t):
            return True

    # ── 3. Length fallback ────────────────────────────────────────
    # Very short queries with no task words are conversational
    if len(t.split()) <= 5:
        return True

    return False


class NexusOrchestrator:
    """
    Central orchestrator for NEXUS AI.
    Builds and runs the agent pipeline for any given task.
    """

    def __init__(self, model_client):
        self.client    = model_client
        self.planner   = PlannerAgent(model_client)
        self.researcher= ResearcherAgent(model_client)
        self.coder     = CoderAgent(model_client)
        self.analyst   = AnalystAgent(model_client)
        self.critic    = CriticAgent(model_client)
        self.optimizer = OptimizerAgent(model_client)
        self.validator = ValidatorAgent(model_client)
        self.reporter  = ReporterAgent(model_client)

        self._agent_map = {
            "Researcher": self.researcher,
            "Coder":      self.coder,
            "Analyst":    self.analyst,
            "Reporter":   self.reporter,
        }

        # Initialise Day 4 memory layers
        self._init_memory()

    async def _llm_call(self, model_client, system: str, user: str) -> str:
        """Direct LLM call used for fact extraction."""
        from autogen_core.models import UserMessage, SystemMessage
        r = await model_client.create(messages=[
            SystemMessage(content=system),
            UserMessage(content=user, source="nexus"),
        ])
        c = r.content
        if isinstance(c, list):
            c = " ".join(p.text if hasattr(p, "text") else str(p) for p in c)
        return (c or "").strip()

    def _init_memory(self):
        """Initialise Day 4 memory layers. Called from __init__."""
        if not MEMORY_AVAILABLE:
            self.session = self.vector = self.ltm = None
            return
        from nexus_ai.config import NEXUS_DIR
        mem_path = NEXUS_DIR / "memory_store"
        mem_path.mkdir(exist_ok=True)
        self.session = SessionMemory(window=10)
        self.vector  = VectorStore(store_path=str(mem_path), top_k=3)
        self.ltm     = LongTermMemory(db_path=str(mem_path / "nexus_memory.db"))
        log.info("Memory initialised",
                 vectors=self.vector.count, facts=self.ltm.count)

    async def run(
        self,
        task:       str,
        file_path:  str | None = None,
        db_path:    str | None = None,
        save_to:    str | None = None,
        on_update:  callable   = None,
    ) -> dict:
        """
        Run the full NEXUS pipeline for a task.

        Args:
            task:       User's task string
            file_path:  Optional file to give Researcher/Analyst
            db_path:    Optional SQLite DB to give Analyst
            save_to:    Optional path to save Reporter output
            on_update:  Optional callback(step: str, content: str) for streaming UI

        Returns:
            {
              "answer":     str,           final answer from Reporter
              "plan":       dict,          execution plan from Planner
              "trace":      list[dict],    per-agent results
              "score":      int,           final validator score
              "approved":   bool,
              "duration_s": float,
            }
        """
        t0 = time.time()
        log.pipeline_start(task)

        def emit(step: str, content: str, output: str = ""):
            if on_update:
                on_update(step, content, output)
            log.info(f"[{step}] {content[:100]}")

        trace   = []
        context = ""

        # ── Memory recall ─────────────────────────────────────────
        if self.session and self.vector and self.ltm:
            parts = []

            # Detect if this is a follow-up needing full previous context
            # e.g. "save this as...", "summarise the above", "based on that"
            FOLLOWUP_SIGNALS = [
                "save this", "save the", "save it", "save as",
                "based on that", "based on the above", "from the above",
                "the above", "previous answer", "that report", "this report",
                "what you just", "you just said", "you mentioned",
                "expand on", "elaborate on", "more detail on",
                "summarise the", "summarize the",
            ]
            needs_full = any(sig in task.lower() for sig in FOLLOWUP_SIGNALS)

            s = self.session.recall_context(full=needs_full)
            if s: parts.append(s)
            v = self.vector.recall_context(task)
            if v: parts.append(v)
            kw = task.split()[0] if task else ""
            l = self.ltm.get_as_context(keyword=kw, n=3, query=task)
            if l: parts.append(l)
            if parts:
                memory_context = "\n\n".join(parts)
                context = f"[Relevant memory from past sessions]\n{memory_context}\n\n"
                emit("Memory",
                     f"Recalled {len(parts)} layer(s) "
                     f"({'full' if needs_full else 'summary'} context, "
                     f"{len(memory_context)} chars)")

        # ── Fast path: save commands ──────────────────────────────
        # Detect any intent to save the last answer to a file.
        # Uses LLM-free heuristic: does the message contain a filename
        # AND a save-intent word? Then confirm with a quick LLM check.
        def _detect_save(text: str) -> str | None:
            """
            Return the target filename if this looks like a save command,
            None otherwise. Uses two layers:
              1. Fast: filename present + save-intent keyword
              2. If ambiguous: fall through to pipeline
            """
            import re as _re
            # Must contain a filename with a writable extension
            fname_match = _re.search(
                r'[\w./\-]+\.(?:md|txt|py|json|yaml|yml|html|csv)',
                text, _re.I
            )
            if not fname_match:
                return None

            # Save-intent words — broad, catches natural language variations
            SAVE_WORDS = [
                "save", "store", "write", "export", "dump", "put",
                "create", "generate", "output", "make", "produce",
            ]
            t_lower = text.lower()
            has_save_intent = any(w in t_lower for w in SAVE_WORDS)
            if not has_save_intent:
                return None

            # Must also reference previous content — not just "create a new file"
            REF_WORDS = [
                "this", "it", "that", "the report", "the answer",
                "the analysis", "the above", "previous", "last",
                "generated", "findings", "result", "content", "there",
            ]
            has_reference = any(w in t_lower for w in REF_WORDS)
            if not has_reference:
                return None

            return fname_match.group(0)

        save_filename = _detect_save(task)
        if save_filename:
            # Get last assistant answer — try session turns first,
            # then fall back to the recalled memory context
            last_answer = None

            # 1. Try session turns (in-memory, current session)
            if self.session:
                for turn in reversed(self.session._turns):
                    if turn.role == "assistant" and len(turn.content) > 100:
                        last_answer = turn.content
                        break

            # 2. Fall back to recalled memory context (persisted from prev sessions)
            if not last_answer and context:
                # Extract the assistant's last response from the context string
                # context format: "── Recent conversation ──\nUser: ...\nAssistant: ..."
                import re as _re2
                matches = _re2.findall(
                    r'Assistant:\s*(.+?)(?=\nUser:|\Z)', context, _re2.DOTALL
                )
                if matches:
                    candidate = matches[-1].strip()
                    if len(candidate) > 100:
                        last_answer = candidate

            if last_answer:
                from pathlib import Path as _Path
                root = _Path(__file__).resolve().parent.parent
                out_path = root / save_filename
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(last_answer, encoding="utf-8")
                msg = f"✅ Saved to `{save_filename}` ({len(last_answer)} chars)"
                emit("NEXUS", f"Saving to {save_filename}...")
                if self.session:
                    self.session.add_user(task)
                    self.session.add_assistant(msg)
                duration = time.time() - t0
                log.pipeline_end(task, duration, success=True)
                return {
                    "answer":     msg,
                    "plan":       {"task_type": "save", "complexity": "simple", "steps": []},
                    "trace":      [{"agent": "NEXUS (save)", "output": msg}],
                    "score":      10,
                    "approved":   True,
                    "duration_s": round(duration, 2),
                }
            # No last answer found — fall through to pipeline
        # Greetings, introductions, follow-ups, short factual questions
        # are answered directly using memory context + one LLM call.
        # Only tasks that genuinely need planning, tools, or research
        # go through the full multi-agent pipeline.
        if _is_simple(task):
            emit("NEXUS", "Simple message — answering directly...")
            SIMPLE_SYS = """\
You are NEXUS AI, a helpful assistant with memory of past conversations.
Answer the user's message naturally and concisely.
If memory context is provided, use it to personalise your response.
Do not mention agents, pipelines, or internal systems.\
"""
            answer = await self._llm_call(
                self.client, SIMPLE_SYS,
                f"{task}\n\n{context}" if context else task,
            )
            # Store in memory — session always, vector+LTM only if facts found
            if self.session:
                self.session.add_user(task)
                self.session.add_assistant(answer)   # ← full answer
            # Simple messages rarely contain storable facts
            # but introductions like "my name is X" should be stored
            if self.vector and self.ltm:
                intro_patterns = [
                    r"my name is (\w+)",
                    r"i am (\w+)",
                    r"i'm (\w+)",
                    r"i work (.*)",
                    r"i like (.*)",
                    r"i love (.*)",
                ]
                for pattern in intro_patterns:
                    m = re.search(pattern, task.lower())
                    if m:
                        fact = task.strip()
                        # Check not already stored
                        existing = self.ltm.get_recent(n=10)
                        already  = any(fact.lower() in f["fact"].lower()
                                       for f in existing)
                        if not already:
                            self.vector.store_fact(fact)
                            self.ltm.store(fact, source="fact", tags=["personal"])
                        break

            duration = time.time() - t0
            log.pipeline_end(task, duration, success=True)
            trace.append({"agent": "NEXUS (direct)", "output": answer})
            return {
                "answer":     answer,
                "plan":       {"task_type": "simple", "complexity": "simple", "steps": []},
                "trace":      trace,
                "score":      10,
                "approved":   True,
                "duration_s": round(duration, 2),
            }

        # ── Step 1: Plan ─────────────────────────────────────────
        from datetime import datetime
        today = datetime.now().strftime("%B %d, %Y")
        emit("Planner", "Building execution plan...")
        plan  = await self.planner.run(
            f"[Today's date: {today}]\n{task}"
        )
        steps = plan.get("steps", [])

        # ── Enforce Critic for code/complex tasks ─────────────────
        # Small models sometimes omit Critic even when told to include it.
        # If task has Coder steps and no Critic, inject Critic+Optimizer
        # before Reporter automatically.
        agent_names = [s["agent"] for s in steps]
        has_coder   = "Coder" in agent_names
        has_critic  = "Critic" in agent_names
        complexity  = plan.get("complexity", "simple")

        if (has_coder or complexity != "simple") and not has_critic:
            # Find Reporter position and inject before it
            reporter_idx = next(
                (i for i, s in enumerate(steps) if s["agent"] == "Reporter"),
                len(steps),
            )
            next_id = reporter_idx + 1
            steps.insert(reporter_idx, {
                "step": next_id,
                "agent": "Optimizer",
                "instruction": "Improve the output based on Critic feedback",
            })
            steps.insert(reporter_idx, {
                "step": next_id,
                "agent": "Critic",
                "instruction": f"Review quality, completeness, and correctness for: {task[:100]}",
            })
            # Renumber steps
            for i, s in enumerate(steps, 1):
                s["step"] = i
            plan["steps"] = steps
            emit("Planner", "⚠️  Critic not in plan — injected automatically")
        agents_in_plan = [s['agent'] for s in steps]
        plan_text = (
            f"Task type : {plan.get('task_type','?')}  |  "
            f"Complexity: {plan.get('complexity','?')}\n"
            f"Pipeline  : {' → '.join(agents_in_plan)}\n\n"
            + "\n".join(
                f"  Step {s['step']}: [{s['agent']}]\n"
                f"    {s['instruction'][:120]}"
                for s in steps
            )
        )
        emit("__output__", "Planner", plan_text)
        trace.append({"agent": "Planner", "output": str(plan)})

        # ── Step 2: Run planned agents ────────────────────────────
        content_for_quality = ""
        # db_path can be passed by user (/db flag) or auto-detected
        # from Coder output after it creates a .db file
        active_db_path = db_path

        for step_def in steps:
            agent_name  = step_def.get("agent", "")
            instruction = step_def.get("instruction", task)

            emit(agent_name, instruction[:80])

            if agent_name == "Researcher":
                output = await self.researcher.run(
                    instruction, context, file_path=file_path
                )
            elif agent_name == "Coder":
                output = await self.coder.run(instruction, context)
                # Auto-detect any .db file Coder just created
                # so a subsequent Analyst step gets the right db_path
                import re as _re
                db_match = _re.search(r'[\w./\-]+\.db', output)
                if db_match:
                    import os as _os
                    candidate = db_match.group(0)
                    if _os.path.exists(candidate):
                        active_db_path = candidate
                        emit("Coder", f"DB created → {candidate} (passing to Analyst)")

            elif agent_name == "Analyst":
                output = await self.analyst.run(
                    instruction, context,
                    file_path=file_path,
                    db_path=active_db_path,   # uses user-provided OR Coder-created
                )
            elif agent_name == "Reporter":
                content_for_quality = context
                continue
            elif agent_name in ("Critic", "Optimizer", "Validator"):
                # These run in the dedicated quality loop — skip silently here
                continue
            else:
                agent = self._agent_map.get(agent_name)
                if agent:
                    output = await agent.run(instruction, context)
                else:
                    output = f"[{agent_name} not found — skipped]"
                    emit(agent_name, output)
                    continue

            context += f"\n\n── {agent_name} ──\n{output}"
            trace.append({"agent": agent_name, "output": output})
            emit("__output__", agent_name, output)

        # ── Step 3: Quality loop ──────────────────────────────────
        # Flow per cycle:
        #   Critic   → reads actual files, scores real code
        #   if poor → Coder fixes files + Optimizer improves docs
        #   Critic   → reviews again (max MAX_QUALITY_RETRIES cycles)
        #   Validator → final gate (always runs once)
        #   Reporter  → final answer (always runs once)
        use_quality_loop = any(s["agent"] in ("Critic", "Optimizer") for s in steps)
        task_has_code    = any(s["agent"] == "Coder" for s in steps)

        if use_quality_loop:
            for attempt in range(1, MAX_QUALITY_RETRIES + 1):

                # ── Critic: reads files from disk, scores real code ──
                emit("Critic", f"Quality review (attempt {attempt}/{MAX_QUALITY_RETRIES})...")
                critique = await self.critic.run(task, context)
                score    = critique.get("score", 7)
                verdict  = critique.get("verdict", "pass")
                gaps     = critique.get("gaps", [])
                improve  = critique.get("improvement_instructions", "")
                trace.append({"agent": "Critic", "output": critique, "attempt": attempt})
                emit("__output__", "Critic",
                     f"Score: {score}/10 | {verdict}\n"
                     f"Gaps:\n" + "\n".join(f"  - {g}" for g in gaps) +
                     f"\nInstructions: {improve[:300]}")

                if score >= MIN_QUALITY_SCORE or verdict == "pass":
                    emit("Critic", "Quality approved ✅")
                    break

                if attempt == MAX_QUALITY_RETRIES:
                    emit("Critic", "Max retries reached — proceeding with best available")
                    break

                if task_has_code:
                    # ── Planner: targeted fix plan (Coder only) ──────
                    emit("Planner", f"Re-planning fix (attempt {attempt})...")
                    fix_plan  = await self.planner.run(
                        f"Fix these gaps in the code:\n"
                        + "\n".join(f"  - {g}" for g in gaps) +
                        f"\n\nInstructions: {improve}\n\nTask: {task}\n\n"
                        f"Steps for ONLY Coder — write files with open(), no servers.",
                        context,
                    )
                    fix_steps = [
                        s for s in fix_plan.get("steps", [])
                        if s.get("agent") in {"Coder", "Researcher", "Analyst"}
                    ] or [{"step": 1, "agent": "Coder", "instruction": improve}]

                    emit("__output__", "Planner",
                         "Fix plan: " + " → ".join(s["agent"] for s in fix_steps) + "\n" +
                         "\n".join(f"  [{s['agent']}] {s['instruction'][:100]}"
                                   for s in fix_steps))
                    trace.append({"agent": "Planner (fix)", "output": str(fix_plan),
                                  "attempt": attempt})

                    # ── Coder: writes the actual file fixes to disk ──
                    for fix_step in fix_steps:
                        fa = fix_step.get("agent", "Coder")
                        fi = fix_step.get("instruction", improve)
                        emit(fa, f"[Fix] {fi[:80]}")
                        if fa == "Coder":
                            fo = await self.coder.run(fi, context)
                        elif fa == "Researcher":
                            fo = await self.researcher.run(fi, context, file_path=file_path)
                        elif fa == "Analyst":
                            fo = await self.analyst.run(fi, context,
                                                        file_path=file_path,
                                                        db_path=active_db_path)
                        else:
                            continue
                        context += f"\n\n── Coder fix {attempt} ──\n{fo}"
                        trace.append({"agent": f"{fa} (fix)", "output": fo, "attempt": attempt})
                        emit("__output__", f"{fa} (fix)", fo)

                    # ── Optimizer: improves files + docs after Coder ──
                    emit("Optimizer", f"Improving files and docs (attempt {attempt})...")
                    improved = await self.optimizer.run(
                        original_output=context,
                        critic_feedback=critique,
                        original_task=task,
                    )
                    context += f"\n\n── Optimizer {attempt} ──\n{improved}"
                    trace.append({"agent": "Optimizer", "output": improved, "attempt": attempt})
                    emit("__output__", "Optimizer", improved)

                else:
                    # ── Text task: Optimizer rewrites content ─────────
                    emit("Optimizer", f"Rewriting (attempt {attempt})...")
                    improved = await self.optimizer.run(
                        original_output=context,
                        critic_feedback=critique,
                        original_task=task,
                    )
                    context += f"\n\n── Optimizer {attempt} ──\n{improved}"
                    trace.append({"agent": "Optimizer", "output": improved, "attempt": attempt})
                    emit("__output__", "Optimizer", improved)

        # ── Step 4: Validate ─────────────────────────────────────
        emit("Validator", "Final validation...")
        validation = await self.validator.run(context, task)
        approved   = validation.get("approved", True)
        val_score  = validation.get("score", 7)
        val_reason = validation.get("reason", "")
        final_text = validation.get("final_output", context)
        unmet      = validation.get("unmet_requirements", [])
        trace.append({"agent": "Validator", "output": validation})
        emit("__output__", "Validator",
             f"{'Approved ✅' if approved else 'Flagged ⚠️'} | score={val_score}/10\n"
             f"Reason: {val_reason}")

        # ── Step 4b: Post-validation fix (one attempt) ────────────
        # When Validator flags ANY failure, feed the reason + unmet requirements
        # back to the SAME Planner and let it decide what agents fix it.
        # This is universal — works for missing files, incomplete endpoints,
        # wrong content, missing sections, wrong format, etc.
        if not approved:
            emit("Planner",
                 f"Validator flagged (score {val_score}/10) — re-planning fix...")

            # Give Planner everything it needs: original task + what failed + full context
            fix_prompt = (
                f"The output for this task was flagged by the Validator.\n\n"
                f"Original task: {task}\n\n"
                f"Validator reason: {val_reason}\n"
                f"Unmet requirements:\n"
                + "\n".join(f"  - {r}" for r in unmet) +
                f"\n\nAll previous work is in the context below. "
                f"Create a minimal plan to fix ONLY what the Validator flagged.\n"
                f"Do NOT redo work that is already done.\n"
                f"If files need to be written to disk: use Coder with open().\n"
                f"If content needs improvement: use Optimizer.\n"
                f"If more research is needed: use Researcher.\n"
                f"Do NOT include Critic, Validator, or Reporter in fix steps."
            )

            fix_plan  = await self.planner.run(fix_prompt, context)
            fix_steps = fix_plan.get("steps", [])

            # Filter to only executable agents — Planner sometimes ignores instructions
            executable = {"Coder", "Researcher", "Analyst", "Optimizer"}
            fix_steps  = [s for s in fix_steps if s.get("agent") in executable]

            # If Planner returned nothing useful, default to Coder for file issues
            # or Optimizer for content issues
            if not fix_steps:
                has_file_issue = any(w in val_reason.lower() for w in [
                    "file", "folder", "disk", "directory", "missing", "not created",
                    "not found", "saved", "written", "exist",
                ])
                default_agent = "Coder" if has_file_issue else "Optimizer"
                default_instr = (
                    f"Fix the following for task '{task[:80]}':\n{val_reason}\n"
                    f"Unmet: {', '.join(unmet)}\n"
                    f"Use content from context. Write files with open() if needed."
                )
                fix_steps = [{"step": 1, "agent": default_agent,
                               "instruction": default_instr}]

            emit("__output__", "Planner",
                 f"Fix plan: {' → '.join(s['agent'] for s in fix_steps)}\n" +
                 "\n".join(f"  [{s['agent']}] {s['instruction'][:100]}"
                           for s in fix_steps))
            trace.append({"agent": "Planner (post-fix)", "output": str(fix_plan)})

            # Run each fix step through the same agent routing as the main loop
            for fix_step in fix_steps:
                fa = fix_step.get("agent", "Coder")
                fi = fix_step.get("instruction", val_reason)
                emit(fa, f"[Post-fix] {fi[:80]}")

                if fa == "Coder":
                    fo = await self.coder.run(fi, context)
                elif fa == "Researcher":
                    fo = await self.researcher.run(fi, context, file_path=file_path)
                elif fa == "Analyst":
                    fo = await self.analyst.run(fi, context,
                                                file_path=file_path,
                                                db_path=active_db_path)
                elif fa == "Optimizer":
                    # Optimizer needs critic_feedback format
                    fo = await self.optimizer.run(
                        original_output=context,
                        critic_feedback={
                            "gaps": unmet or [val_reason],
                            "improvement_instructions": fi,
                            "score": val_score,
                        },
                        original_task=task,
                    )
                else:
                    continue

                context += f"\n\n── Post-fix [{fa}] ──\n{fo}"
                trace.append({"agent": f"{fa} (post-fix)", "output": fo})
                emit("__output__", f"{fa} (post-fix)", fo)

            # Re-validate once after all fix steps
            emit("Validator", "Re-validating after post-fix...")
            validation2 = await self.validator.run(context, task)
            approved    = validation2.get("approved", True)
            val_score   = validation2.get("score", val_score)
            final_text  = validation2.get("final_output", context)
            trace.append({"agent": "Validator (re-check)", "output": validation2})
            emit("__output__", "Validator",
                 f"{'Approved ✅' if approved else 'Still flagged ⚠️'} | "
                 f"score={val_score}/10\n"
                 f"Reason: {validation2.get('reason', '')}")

        # ── Step 5: Report ────────────────────────────────────────
        emit("Reporter", "Writing final answer...")
        # If Validator flagged, tell Reporter so it can note any caveats
        reporter_context = final_text
        if not approved:
            reporter_context = (
                f"[Note: Validator flagged this output — score {val_score}/10. "
                f"Reason: {validation.get('reason','')}. "
                f"Present the best available information but note any gaps.]\n\n"
                + final_text
            )
        answer = await self.reporter.run(task, reporter_context, save_to=save_to)
        trace.append({"agent": "Reporter", "output": answer})
        emit("__output__", "Reporter", answer)

        # ── Memory store ──────────────────────────────────────────
        if self.session and self.vector and self.ltm:
            # Session: store full turns — no truncation
            # Session window=10 handles memory management automatically
            self.session.add_user(task)
            self.session.add_assistant(answer)

            # Vector + LTM: facts ONLY — no raw Q&A episodes
            # Pass full answer to fact extractor so long reports aren't missed
            existing_facts = self.ltm.get_recent(n=20)
            existing_text  = "\n".join(f"- {f['fact']}" for f in existing_facts) or "None."

            FACT_SYS = """\
You are a memory manager. Extract only NEW, reusable facts from this exchange.

ALREADY STORED FACTS:
{existing}

NEW EXCHANGE:
Task: {task}
Answer: {answer}

Extract facts that are:
  1. NEW — not already in stored facts above
  2. PERSONAL or FACTUAL — about the user, their work, preferences, or domain knowledge
  3. REUSABLE — worth remembering for future tasks

Do NOT store:
  - Duplicates of existing facts
  - Procedural steps or code snippets
  - Greetings or acknowledgements
  - Task descriptions (only outcomes/facts)

Output JSON array of objects: [{{"fact": "...", "tag": "personal|work|knowledge|preference|other"}}]
Empty array [] if nothing new.
Raw JSON only. No fences.\
"""
            try:
                raw_facts = await self._llm_call(
                    self.client,
                    FACT_SYS.format(
                        existing=existing_text,
                        task=task,
                        answer=answer,          # ← full answer, no truncation
                    ),
                    "Extract new facts:",
                )
                raw_facts = re.sub(r"```(?:json)?", "", raw_facts).strip().rstrip("`")
                parsed = json.loads(raw_facts)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "fact" in item:
                            fact = item["fact"].strip()
                            tag  = item.get("tag", "other")
                        elif isinstance(item, str):
                            fact, tag = item.strip(), "other"
                        else:
                            continue
                        if fact:
                            self.vector.store_fact(fact)
                            self.ltm.store(fact, source="fact", tags=[tag])
            except Exception:
                pass  # best-effort

            emit("Memory", f"Stored → session={self.session.turn_count} "
                           f"| vectors={self.vector.count} | facts={self.ltm.count}")

        duration = time.time() - t0
        log.pipeline_end(task, duration, success=True)

        return {
            "answer":     answer,
            "plan":       plan,
            "trace":      trace,
            "score":      val_score,
            "approved":   approved,
            "duration_s": round(duration, 2),
        }