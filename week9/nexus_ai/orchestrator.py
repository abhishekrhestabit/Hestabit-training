import inspect
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from nexus_ai.config import (
    MAX_QUALITY_RETRIES,
    MIN_QUALITY_SCORE,
    POST_VALIDATION_REPLAN_MAX_SCORE,
    get_fallback_providers,
    get_model_client,
    get_runtime_client,
    get_runtime_provider,
    set_runtime_client,
)
from nexus_ai.agents import (
    AnalystAgent,
    CoderAgent,
    CriticAgent,
    OptimizerAgent,
    PlannerAgent,
    ReporterAgent,
    ResearcherAgent,
    ValidatorAgent,
)
from nexus_ai.logger import log
from nexus_ai.pipeline_state import PipelineState
from nexus_ai.task_utils import (
    is_local_build_task,
    is_simple_task,
    needs_explicit_research,
    slugify_task,
)
from nexus_ai.workspace_manager import create_task_workspace

try:
    from memory.long_term import LongTermMemory
    from memory.session_memory import SessionMemory
    from memory.vector_store import VectorStore

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    log.warn("Memory modules not found — running without memory")


class NexusOrchestrator:
    FOLLOWUP_CONTEXT_SIGNALS = [
        "based on the above", "based on that", "based on this",
        "previous answer", "previous output", "continue this",
        "continue from", "extend this", "extend the", "integrate",
        "merge", "combine", "refactor this", "use the above",
        "the code above", "the earlier", "what you just",
        "you just said", "from the previous",
    ]

    MEMORY_FOLLOWUP_SIGNALS = [
        "save this", "save the", "save it", "save as",
        "based on that", "based on the above", "from the above",
        "the above", "previous answer", "that report", "this report",
        "what you just", "you just said", "you mentioned",
        "expand on", "elaborate on", "more detail on",
        "summarise the", "summarize the",
    ]

    FILE_REF_PATTERN = re.compile(
        r"(?:(?:[\w\-]+/)*)[\w\-]+\.(?:py|txt|md|yaml|yml|json|html|js|ts|css|db|csv)",
        re.I,
    )

    def __init__(self, model_client):
        self.client = model_client
        self.planner = PlannerAgent(model_client)
        self.researcher = ResearcherAgent(model_client)
        self.coder = CoderAgent(model_client)
        self.analyst = AnalystAgent(model_client)
        self.critic = CriticAgent(model_client)
        self.optimizer = OptimizerAgent(model_client)
        self.validator = ValidatorAgent(model_client)
        self.reporter = ReporterAgent(model_client)
        self._agent_map = {
            "Researcher": self.researcher,
            "Coder": self.coder,
            "Analyst": self.analyst,
            "Reporter": self.reporter,
        }
        self._init_memory()

    @staticmethod
    def _stringify_output(output: Any) -> str:
        if isinstance(output, str):
            return output
        try:
            return json.dumps(output, indent=2, ensure_ascii=False)
        except Exception:
            return str(output)

    @staticmethod
    def _combine_context(*parts: str) -> str:
        return "\n\n".join(part.strip() for part in parts if part and part.strip())

    @staticmethod
    def _append_context_block(context: str, label: str, output: Any) -> str:
        block = f"── {label} ──\n{NexusOrchestrator._stringify_output(output)}"
        return f"{context}\n\n{block}".strip() if context else block

    @staticmethod
    def _agent_base_name(agent_name: str) -> str:
        return agent_name.split(" (", 1)[0]

    @staticmethod
    def _is_retryable_provider_error(error: Exception) -> bool:
        text = str(error).lower()
        signals = [
            "rate limit", "rate_limit", "429", "quota",
            "resource exhausted", "too many requests", "503",
            "service unavailable", "currently experiencing high demand",
            "unavailable", "overloaded",
        ]
        return any(signal in text for signal in signals)

    def _emit(self, state: PipelineState, step: str, content: str, output: str = "") -> None:
        if state.on_update:
            state.on_update(step, content, output)
        log.info(f"[{step}] {content[:100]}")

    def _record_trace(self, state: PipelineState, agent: str, output: Any, **extra: Any) -> None:
        item = {"agent": agent, "output": output}
        item.update(extra)
        state.trace.append(item)

    def _new_state(
        self,
        task: str,
        file_path: str | None,
        db_path: str | None,
        save_to: str | None,
        on_update: Callable[[str, str, str], None] | None,
    ) -> PipelineState:
        return PipelineState(
            task=task,
            file_path=file_path,
            db_path=db_path,
            save_to=save_to,
            on_update=on_update,
            active_db_path=db_path,
        )

    def _workspace_note(self, state: PipelineState) -> str:
        return "\n".join(
            [
                "[Task workspace]",
                f"Write any generated files for this task inside: {state.task_workspace_rel}",
                "Use task-specific subpaths inside that folder when multiple files are needed.",
                "Do not create nested ./workspace/workspace paths.",
                "Print each created or updated file path in the final program output.",
            ]
        )

    def _prepend_base_context(self, state: PipelineState, text: str) -> None:
        state.base_context = self._combine_context(text, state.base_context)

    def _prepare_memory(self, state: PipelineState) -> None:
        if not (self.session and self.vector and self.ltm):
            return

        needs_full = any(signal in state.task.lower() for signal in self.MEMORY_FOLLOWUP_SIGNALS)
        parts = []
        session_context = self.session.recall_context(full=needs_full)
        vector_context = self.vector.recall_context(state.task)
        keyword = state.task.split()[0] if state.task else ""
        long_term_context = self.ltm.get_as_context(keyword=keyword, n=3, query=state.task)

        for part in (session_context, vector_context, long_term_context):
            if part:
                parts.append(part)

        if not parts:
            return

        memory_context = "\n\n".join(parts)
        self._prepend_base_context(
            state,
            f"[Relevant memory from past sessions]\n{memory_context}",
        )
        self._emit(
            state,
            "Memory",
            f"Recalled {len(parts)} layer(s) "
            f"({'full' if needs_full else 'summary'} context, {len(memory_context)} chars)",
        )

    async def _suggest_workspace_label(self, state: PipelineState) -> str:
        system = (
            "Return a short folder label for this task.\n"
            "Rules:\n"
            "- lowercase words joined with underscores\n"
            "- 4 to 10 words\n"
            "- no dates\n"
            "- no punctuation except underscores\n"
            "- focus on the main deliverable\n"
            "Return the label only."
        )
        try:
            raw = await self._llm_call(self.client, system, state.task)
        except Exception:
            raw = state.task
        label = slugify_task(raw)
        return label or slugify_task(state.task)

    async def _ensure_task_workspace(self, state: PipelineState) -> None:
        if state.task_workspace_rel and state.task_workspace_abs:
            return
        label = await self._suggest_workspace_label(state)
        rel, abs_path = create_task_workspace(state.task, folder_label=label)
        state.task_workspace_rel = rel
        state.task_workspace_abs = abs_path
        self._prepend_base_context(state, self._workspace_note(state))

    def _extract_last_answer(self, state: PipelineState) -> str | None:
        if self.session:
            for turn in reversed(self.session._turns):
                if turn.role == "assistant" and len(turn.content) > 100:
                    return turn.content

        matches = re.findall(r"Assistant:\s*(.+?)(?=\nUser:|\Z)", state.base_context, re.DOTALL)
        if matches:
            candidate = matches[-1].strip()
            if len(candidate) > 100:
                return candidate
        return None

    @staticmethod
    def _detect_save(text: str) -> str | None:
        filename = re.search(r"[\w./\-]+\.(?:md|txt|py|json|yaml|yml|html|csv)", text, re.I)
        if not filename:
            return None

        lowered = text.lower()

        explicit_patterns = [
            r"\bsave\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(filename.group(0).lower()),
            r"\bstore\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(filename.group(0).lower()),
            r"\bexport\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(filename.group(0).lower()),
            r"\bdump\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(filename.group(0).lower()),
            r"\bwrite\b.{0,80}\b(?:to|into|in|as)\b.{0,80}" + re.escape(filename.group(0).lower()),
            r"\bput\b.{0,80}\b(?:to|into|in)\b.{0,80}" + re.escape(filename.group(0).lower()),
            r"\b" + re.escape(filename.group(0).lower()) + r"\b.{0,40}\b(?:save|store|export|dump)\b",
        ]
        if not any(re.search(pattern, lowered, re.DOTALL) for pattern in explicit_patterns):
            return None

        ref_words = [
            "this", "it", "that", "the report", "the answer",
            "the analysis", "the above", "previous", "last",
            "generated", "findings", "result", "content", "there",
        ]
        if not any(word in lowered for word in ref_words):
            return None
        return filename.group(0)

    def _build_result(self, state: PipelineState, answer: str, *, score: int, approved: bool) -> dict:
        duration = time.time() - state.started_at
        log.pipeline_end(state.task, duration, success=True)
        return {
            "answer": answer,
            "plan": state.plan,
            "trace": state.trace,
            "score": score,
            "approved": approved,
            "duration_s": round(duration, 2),
        }

    def _maybe_handle_save_command(self, state: PipelineState) -> dict | None:
        save_filename = self._detect_save(state.task)
        if not save_filename:
            return None

        last_answer = self._extract_last_answer(state)
        if not last_answer:
            return None

        out_path = Path(__file__).resolve().parent.parent / save_filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(last_answer, encoding="utf-8")
        message = f"✅ Saved to `{save_filename}` ({len(last_answer)} chars)"
        self._emit(state, "NEXUS", f"Saving to {save_filename}...")
        if self.session:
            self.session.add_user(state.task)
            self.session.add_assistant(message)
        state.plan = {"task_type": "save", "complexity": "simple", "steps": []}
        self._record_trace(state, "NEXUS (save)", message)
        return self._build_result(state, message, score=10, approved=True)

    async def _maybe_handle_simple_task(self, state: PipelineState) -> dict | None:
        if not is_simple_task(state.task):
            return None

        self._emit(state, "NEXUS", "Simple message — answering directly...")
        system = (
            "You are NEXUS AI, a helpful assistant with memory of past conversations.\n"
            "Answer the user's message naturally and concisely.\n"
            "If memory context is provided, use it to personalise your response.\n"
            "Do not mention agents, pipelines, or internal systems."
        )
        answer = await self._llm_call(
            self.client,
            system,
            f"{state.task}\n\n{state.base_context}" if state.base_context else state.task,
        )

        if self.session:
            self.session.add_user(state.task)
            self.session.add_assistant(answer)
        if self.vector and self.ltm:
            for pattern in [r"my name is (\w+)", r"i am (\w+)", r"i'm (\w+)", r"i work (.*)", r"i like (.*)", r"i love (.*)"]:
                if re.search(pattern, state.task.lower()):
                    fact = state.task.strip()
                    existing = self.ltm.get_recent(n=10)
                    if not any(fact.lower() in item["fact"].lower() for item in existing):
                        self.vector.store_fact(fact)
                        self.ltm.store(fact, source="fact", tags=["personal"])
                    break

        state.plan = {"task_type": "simple", "complexity": "simple", "steps": []}
        self._record_trace(state, "NEXUS (direct)", answer)
        return self._build_result(state, answer, score=10, approved=True)

    def _should_skip_researcher(self, state: PipelineState, steps: list[dict]) -> bool:
        if state.file_path:
            return False
        step_agents = {step.get("agent", "") for step in steps}
        if "Researcher" not in step_agents:
            return False
        if "Coder" not in step_agents and "Analyst" not in step_agents:
            return False
        return is_local_build_task(state.task) and not needs_explicit_research(state.task)

    def _normalize_plan_steps(self, state: PipelineState, steps: list[dict]) -> list[dict]:
        normalized = list(steps)
        if self._should_skip_researcher(state, normalized):
            normalized = [step for step in normalized if step.get("agent") != "Researcher"]
        for idx, step in enumerate(normalized, 1):
            step["step"] = idx
        return normalized

    def _ensure_quality_agents(self, state: PipelineState) -> None:
        steps = state.plan.get("steps", [])
        agent_names = [step["agent"] for step in steps]
        has_coder = "Coder" in agent_names
        has_critic = "Critic" in agent_names
        complexity = state.plan.get("complexity", "simple")
        if not ((has_coder or complexity != "simple") and not has_critic):
            return

        reporter_idx = next(
            (idx for idx, step in enumerate(steps) if step["agent"] == "Reporter"),
            len(steps),
        )
        steps.insert(
            reporter_idx,
            {"step": 0, "agent": "Optimizer", "instruction": "Improve the output based on Critic feedback"},
        )
        steps.insert(
            reporter_idx,
            {"step": 0, "agent": "Critic", "instruction": f"Review quality, completeness, and correctness for: {state.task[:100]}"},
        )
        state.plan["steps"] = self._normalize_plan_steps(state, steps)
        self._emit(state, "Planner", "⚠️  Critic not in plan — injected automatically")

    def _render_plan_text(self, state: PipelineState) -> str:
        steps = state.plan.get("steps", [])
        pipeline = " → ".join(step["agent"] for step in steps)
        lines = [
            f"Task type : {state.plan.get('task_type', '?')}  |  Complexity: {state.plan.get('complexity', '?')}",
            f"Pipeline  : {pipeline}",
            "",
        ]
        for step in steps:
            lines.append(f"  Step {step['step']}: [{step['agent']}]")
            lines.append(f"    {step['instruction'][:120]}")
        return "\n".join(lines)

    async def _build_plan(self, state: PipelineState) -> None:
        self._emit(state, "Planner", "Building execution plan...")
        today = datetime.now().strftime("%B %d, %Y")
        state.plan = await self.planner.run(f"[Today's date: {today}]\n{state.task}")
        state.plan["steps"] = self._normalize_plan_steps(state, state.plan.get("steps", []))
        self._ensure_quality_agents(state)
        self._record_trace(state, "Planner", str(state.plan))
        self._emit(state, "__output__", "Planner", self._render_plan_text(state))

    def _trim_text(self, text: str, max_chars: int = 1200) -> str:
        if len(text) <= max_chars:
            return text
        head = max_chars // 2
        tail = max_chars - head - 32
        return text[:head].rstrip() + f"\n...[trimmed {len(text) - max_chars} chars]...\n" + text[-tail:].lstrip()

    def _collect_file_refs(self, state: PipelineState) -> list[str]:
        pool = [state.base_context, state.context]
        pool.extend(self._stringify_output(item.get("output", "")) for item in state.trace)
        refs = set()
        for chunk in pool:
            refs.update(self.FILE_REF_PATTERN.findall(chunk or ""))
            refs.update(re.findall(r"(?:Created|Updated|Wrote|Generated)\s+([\w./\-]+\.\w+)", chunk or "", re.I))
        return sorted(refs)[:20]

    def _should_use_full_context(self, agent_name: str, task: str, instruction: str, full_context: str) -> bool:
        if len(full_context) <= 5000:
            return True
        combined = f"{task}\n{instruction}".lower()
        if any(signal in combined for signal in self.FOLLOWUP_CONTEXT_SIGNALS):
            return True
        if agent_name == "Coder" and any(signal in combined for signal in ["integrate", "merge", "combine", "refactor", "extend"]):
            return True
        return False

    def _build_agent_context(self, state: PipelineState, agent_name: str, instruction: str) -> str:
        full_context = state.combined_context
        if not full_context:
            return ""
        if self._should_use_full_context(agent_name, state.task, instruction, full_context):
            return full_context

        relevant_agents = {
            "Planner": {"Planner", "Researcher", "Coder", "Analyst", "Critic", "Validator", "Optimizer"},
            "Researcher": {"Researcher", "Analyst", "Validator"},
            "Coder": {"Researcher", "Analyst", "Coder", "Critic", "Validator"},
            "Analyst": {"Researcher", "Coder", "Analyst", "Validator"},
            "Critic": {"Researcher", "Coder", "Analyst", "Optimizer", "Validator"},
            "Optimizer": {"Coder", "Analyst", "Critic", "Validator"},
            "Validator": {"Researcher", "Coder", "Analyst", "Critic", "Optimizer"},
        }
        block_limit = {"Planner": 4, "Researcher": 3, "Coder": 4, "Analyst": 4, "Critic": 5, "Optimizer": 4, "Validator": 6}
        selected = [
            item for item in state.trace
            if self._agent_base_name(item.get("agent", "")) in relevant_agents.get(agent_name, set())
        ][-block_limit.get(agent_name, 4):]

        parts = [state.base_context.strip()] if state.base_context else []
        refs = self._collect_file_refs(state)
        if refs:
            parts.append("── Referenced files ──\n" + "\n".join(refs))
        for item in selected:
            label = item.get("agent", "Agent")
            body = self._trim_text(self._stringify_output(item.get("output", "")), max_chars=1400)
            parts.append(f"── {label} ──\n{body}")
        compact = "\n\n".join(part for part in parts if part)
        return compact or full_context

    def _allowed_files(self, state: PipelineState) -> list[str]:
        files = []
        for candidate in (state.file_path, state.db_path, state.active_db_path):
            if candidate:
                files.append(candidate)
        return files

    def _augment_coder_instruction(self, state: PipelineState, instruction: str) -> str:
        extra = [
            f"Write all generated files inside: {state.task_workspace_rel}",
            "Do not write directly into ./workspace/ root when a task-specific folder is provided.",
            "Create complete implementations, not placeholders or toy examples.",
            "Do not add demo seed data or unrelated sample tasks unless explicitly asked.",
            "At the end, print every created or updated file path.",
        ]
        if is_local_build_task(state.task):
            extra.extend([
                "For full backend or system requests, create a proper multi-file project, not a single small script.",
                "Include the layers the task implies, such as database setup, models, schemas, services, routes, and an app entrypoint.",
                "Add real validation, error handling, and configuration choices where they matter.",
                "Do not leave placeholder comments like 'logic defined elsewhere' or 'defined in execution script'.",
            ])
        if any(word in state.task.lower() for word in ["full", "design", "architecture", "system"]):
            extra.append("When helpful, also create a short README or API spec that explains the generated system.")
        return instruction.rstrip() + "\n\n" + "\n".join(f"- {line}" for line in extra)

    def _update_db_path_from_output(self, state: PipelineState, output: str) -> None:
        match = re.search(r"[\w./\-]+\.db", output)
        if not match:
            return
        candidate = match.group(0)
        if Path(candidate).exists():
            state.active_db_path = candidate
            self._emit(state, "Coder", f"DB created → {candidate} (passing to Analyst)")

    async def _run_standard_agent(
        self,
        state: PipelineState,
        agent_name: str,
        instruction: str,
        *,
        phase: str | None = None,
    ) -> str:
        prefix = f"[{phase}] " if phase else ""
        self._emit(state, agent_name, f"{prefix}{instruction[:80]}")
        if agent_name == "Coder":
            await self._ensure_task_workspace(state)
        context = self._build_agent_context(state, agent_name, instruction)
        trace_name = f"{agent_name} ({phase})" if phase else agent_name

        if agent_name == "Researcher":
            output = await self.researcher.run(instruction, context, file_path=state.file_path)
        elif agent_name == "Coder":
            output = await self.coder.run(
                self._augment_coder_instruction(state, instruction),
                context,
                allowed_files=self._allowed_files(state),
                allowed_workspace=state.task_workspace_rel,
            )
            self._update_db_path_from_output(state, output)
        elif agent_name == "Analyst":
            output = await self.analyst.run(
                instruction,
                context,
                file_path=state.file_path,
                db_path=state.active_db_path,
            )
        else:
            agent = self._agent_map.get(agent_name)
            if not agent:
                output = f"[{agent_name} not found — skipped]"
            else:
                output = await agent.run(instruction, context)

        state.context = self._append_context_block(state.context, trace_name, output)
        self._record_trace(state, trace_name, output)
        self._emit(state, "__output__", trace_name, output)
        return output

    async def _execute_plan_steps(self, state: PipelineState) -> None:
        for step in state.plan.get("steps", []):
            agent_name = step.get("agent", "")
            instruction = step.get("instruction", state.task)
            if agent_name in {"Reporter", "Critic", "Optimizer", "Validator"}:
                continue
            await self._run_standard_agent(state, agent_name, instruction)

    async def _run_critic(self, state: PipelineState, attempt: int) -> dict:
        self._emit(state, "Critic", f"Quality review (attempt {attempt}/{MAX_QUALITY_RETRIES})...")
        critique = await self.critic.run(state.task, self._build_agent_context(state, "Critic", state.task))
        self._record_trace(state, "Critic", critique, attempt=attempt)
        gaps = "\n".join(f"  - {gap}" for gap in critique.get("gaps", []))
        summary = (
            f"Score: {critique.get('score', 7)}/10 | {critique.get('verdict', 'pass')}\n"
            f"Gaps:\n{gaps}\n"
            f"Instructions: {critique.get('improvement_instructions', '')[:300]}"
        )
        self._emit(state, "__output__", "Critic", summary)
        return critique

    async def _run_optimizer(
        self,
        state: PipelineState,
        critic_feedback: dict,
        *,
        label: str = "Optimizer",
        attempt: int | None = None,
        message: str = "Improving files and docs...",
    ) -> str:
        self._emit(state, "Optimizer", message if attempt is None else f"{message} (attempt {attempt})...")
        improved = await self.optimizer.run(
            original_output=state.combined_context,
            critic_feedback=critic_feedback,
            original_task=state.task,
        )
        trace_name = label if attempt is None else "Optimizer"
        state.context = self._append_context_block(state.context, trace_name, improved)
        self._record_trace(state, trace_name, improved, **({"attempt": attempt} if attempt is not None else {}))
        self._emit(state, "__output__", trace_name, improved)
        return improved

    async def _request_fix_plan(
        self,
        state: PipelineState,
        *,
        prompt: str,
        planner_hint: str,
        allowed_agents: set[str],
        fallback_step: dict[str, Any] | None = None,
        trace_name: str,
    ) -> tuple[dict, list[dict]]:
        planner_context = self._build_agent_context(state, "Planner", planner_hint)
        fix_plan = await self.planner.run(prompt, planner_context)
        fix_steps = [step for step in fix_plan.get("steps", []) if step.get("agent") in allowed_agents]
        fix_steps = self._normalize_plan_steps(state, fix_steps)
        if not fix_steps and fallback_step:
            fix_steps = [fallback_step]
        self._record_trace(state, trace_name, str(fix_plan))
        return fix_plan, fix_steps

    def _emit_fix_plan(self, state: PipelineState, fix_steps: list[dict]) -> None:
        lines = [f"Fix plan: {' → '.join(step['agent'] for step in fix_steps)}"]
        lines.extend(f"  [{step['agent']}] {step['instruction'][:100]}" for step in fix_steps)
        self._emit(state, "__output__", "Planner", "\n".join(lines))

    async def _execute_fix_steps(
        self,
        state: PipelineState,
        fix_steps: list[dict],
        *,
        phase: str,
        optimizer_feedback: dict | None = None,
    ) -> None:
        for step in fix_steps:
            agent_name = step.get("agent", "Coder")
            instruction = step.get("instruction", state.val_reason or state.task)
            if agent_name == "Optimizer":
                await self._run_optimizer(
                    state,
                    optimizer_feedback or {
                        "gaps": state.unmet or [state.val_reason],
                        "improvement_instructions": instruction,
                        "score": state.val_score,
                    },
                    label=f"Optimizer ({phase})",
                    message=f"Rewriting {phase}",
                )
            else:
                await self._run_standard_agent(state, agent_name, instruction, phase=phase)

    async def _run_quality_loop(self, state: PipelineState) -> None:
        steps = state.plan.get("steps", [])
        if not any(step["agent"] in {"Critic", "Optimizer"} for step in steps):
            return

        task_has_code = any(step["agent"] == "Coder" for step in steps)
        for attempt in range(1, MAX_QUALITY_RETRIES + 1):
            critique = await self._run_critic(state, attempt)
            score = critique.get("score", 7)
            verdict = critique.get("verdict", "pass")

            if score >= MIN_QUALITY_SCORE or verdict == "pass":
                self._emit(state, "Critic", "Quality approved ✅")
                return
            if attempt == MAX_QUALITY_RETRIES:
                self._emit(state, "Critic", "Max retries reached — proceeding with best available")
                return

            if not task_has_code:
                await self._run_optimizer(state, critique, attempt=attempt, message="Rewriting")
                continue

            self._emit(state, "Planner", f"Re-planning fix (attempt {attempt})...")
            prompt = (
                "Fix these gaps in the code:\n"
                + "\n".join(f"  - {gap}" for gap in critique.get("gaps", []))
                + f"\n\nInstructions: {critique.get('improvement_instructions', '')}\n\n"
                + f"Task: {state.task}\n\n"
                + "Steps for ONLY Coder — write files with open(), no servers."
            )
            fallback_step = {"step": 1, "agent": "Coder", "instruction": critique.get("improvement_instructions", "Improve the code.")}
            _, fix_steps = await self._request_fix_plan(
                state,
                prompt=prompt,
                planner_hint=critique.get("improvement_instructions", ""),
                allowed_agents={"Coder", "Researcher", "Analyst"},
                fallback_step=fallback_step,
                trace_name="Planner (fix)",
            )
            self._emit_fix_plan(state, fix_steps)
            await self._execute_fix_steps(state, fix_steps, phase="fix")
            await self._run_optimizer(state, critique, attempt=attempt)

    async def _run_validation(self, state: PipelineState, *, label: str = "Validator", hint: str | None = None) -> dict:
        message = "Final validation..." if label == "Validator" else "Re-validating after post-fix..."
        self._emit(state, "Validator", message)
        validation = await self.validator.run(
            self._build_agent_context(state, "Validator", hint or state.task),
            state.task,
        )
        state.approved = validation.get("approved", True)
        state.val_score = validation.get("score", 7)
        state.val_reason = validation.get("reason", "")
        state.unmet = validation.get("unmet_requirements", [])
        state.final_text = validation.get("final_output", state.combined_context)
        self._record_trace(state, label, validation)
        summary = (
            f"{'Approved ✅' if state.approved else 'Flagged ⚠️'} | score={state.val_score}/10\n"
            f"Reason: {state.val_reason}"
        )
        self._emit(state, "__output__", "Validator", summary)
        return validation

    async def _run_post_validation_fix(self, state: PipelineState) -> None:
        if state.approved or state.val_score > POST_VALIDATION_REPLAN_MAX_SCORE:
            return

        self._emit(state, "Planner", f"Validator flagged (score {state.val_score}/10) — re-planning fix...")
        prompt = (
            "The output for this task was flagged by the Validator.\n\n"
            f"Original task: {state.task}\n\n"
            f"Validator reason: {state.val_reason}\n"
            "Unmet requirements:\n"
            + "\n".join(f"  - {item}" for item in state.unmet)
            + "\n\nAll previous work is in the context below. "
            "Create a minimal plan to fix ONLY what the Validator flagged.\n"
            "Do NOT redo work that is already done.\n"
            "If files need to be written to disk: use Coder with open().\n"
            "If content needs improvement: use Optimizer.\n"
            "If more research is needed: use Researcher.\n"
            "Do NOT include Critic, Validator, or Reporter in fix steps."
        )
        has_file_issue = any(word in state.val_reason.lower() for word in [
            "file", "folder", "disk", "directory", "missing", "not created",
            "not found", "saved", "written", "exist",
        ])
        fallback_agent = "Coder" if has_file_issue else "Optimizer"
        fallback_step = {
            "step": 1,
            "agent": fallback_agent,
            "instruction": (
                f"Fix the following for task '{state.task[:80]}':\n{state.val_reason}\n"
                f"Unmet: {', '.join(state.unmet)}\n"
                "Use content from context. Write files with open() if needed."
            ),
        }
        _, fix_steps = await self._request_fix_plan(
            state,
            prompt=prompt,
            planner_hint=state.val_reason,
            allowed_agents={"Coder", "Researcher", "Analyst", "Optimizer"},
            fallback_step=fallback_step,
            trace_name="Planner (post-fix)",
        )
        if has_file_issue and fix_steps and all(step.get("agent") == "Optimizer" for step in fix_steps):
            fix_steps = [{
                "step": 1,
                "agent": "Coder",
                "instruction": (
                    f"Fix the missing or wrongly written files for task '{state.task[:80]}'.\n"
                    f"Validator reason: {state.val_reason}\n"
                    f"Unmet: {', '.join(state.unmet)}\n"
                    "Write the required files to disk using open() in the expected paths."
                ),
            }]
        self._emit_fix_plan(state, fix_steps)
        await self._execute_fix_steps(state, fix_steps, phase="post-fix")
        await self._run_validation(state, label="Validator (re-check)", hint=state.val_reason)

    async def _write_report(self, state: PipelineState) -> str:
        self._emit(state, "Reporter", "Writing final answer...")
        reporter_context = state.final_text or state.combined_context
        if not state.approved:
            reporter_context = (
                f"[Note: Validator flagged this output — score {state.val_score}/10. "
                f"Reason: {state.val_reason}. Present the best available information but note any gaps.]\n\n"
                + reporter_context
            )
        answer = await self.reporter.run(state.task, reporter_context, save_to=state.save_to)
        self._record_trace(state, "Reporter", answer)
        self._emit(state, "__output__", "Reporter", answer)
        return answer

    async def _store_memory(self, state: PipelineState, answer: str) -> None:
        if not (self.session and self.vector and self.ltm):
            return

        self.session.add_user(state.task)
        self.session.add_assistant(answer)
        existing = self.ltm.get_recent(n=20)
        existing_text = "\n".join(f"- {item['fact']}" for item in existing) or "None."
        fact_system = """\
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
                fact_system.format(existing=existing_text, task=state.task, answer=answer),
                "Extract new facts:",
            )
            raw_facts = re.sub(r"```(?:json)?", "", raw_facts).strip().rstrip("`")
            parsed = json.loads(raw_facts)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "fact" in item:
                        fact = item["fact"].strip()
                        tag = item.get("tag", "other")
                    elif isinstance(item, str):
                        fact, tag = item.strip(), "other"
                    else:
                        continue
                    if fact:
                        self.vector.store_fact(fact)
                        self.ltm.store(fact, source="fact", tags=[tag])
        except Exception:
            pass
        self._emit(
            state,
            "Memory",
            f"Stored → session={self.session.turn_count} | vectors={self.vector.count} | facts={self.ltm.count}",
        )

    async def _llm_call(self, model_client, system: str, user: str) -> str:
        from autogen_core.models import SystemMessage, UserMessage

        current_provider = get_runtime_provider()
        providers_to_try = [current_provider] + get_fallback_providers(current_provider)
        attempted = set()
        last_error = None

        for provider in providers_to_try:
            if provider in attempted:
                continue
            attempted.add(provider)
            try:
                client = model_client if provider == current_provider else get_model_client(
                    provider_override=provider,
                    set_runtime=False,
                )
                if provider != current_provider:
                    set_runtime_client(client, provider)
                    self.client = client
                    current_provider = provider
                    log.warn("Retrying with fallback provider", agent="NEXUS", provider=provider)
                else:
                    client = get_runtime_client()
                    self.client = client
                result = await client.create(
                    messages=[
                        SystemMessage(content=system),
                        UserMessage(content=user, source="nexus"),
                    ]
                )
                content = result.content
                if isinstance(content, list):
                    content = " ".join(part.text if hasattr(part, "text") else str(part) for part in content)
                return (content or "").strip()
            except Exception as error:
                last_error = error
                if provider == current_provider and not self._is_retryable_provider_error(error):
                    raise
                if not self._is_retryable_provider_error(error):
                    continue

        if last_error:
            raise last_error
        raise RuntimeError("No model provider available.")

    def _init_memory(self) -> None:
        if not MEMORY_AVAILABLE:
            self.session = self.vector = self.ltm = None
            return
        from nexus_ai.config import NEXUS_DIR

        mem_path = NEXUS_DIR / "memory_store"
        mem_path.mkdir(exist_ok=True)
        self.session = SessionMemory(window=10)
        self.vector = VectorStore(store_path=str(mem_path), top_k=3)
        self.ltm = LongTermMemory(db_path=str(mem_path / "nexus_memory.db"))
        log.info("Memory initialised", vectors=self.vector.count, facts=self.ltm.count)

    async def run(
        self,
        task: str,
        file_path: str | None = None,
        db_path: str | None = None,
        save_to: str | None = None,
        on_update: Callable[[str, str, str], None] | None = None,
    ) -> dict:
        state = self._new_state(task, file_path, db_path, save_to, on_update)
        log.pipeline_start(task)

        self._prepare_memory(state)

        for fast_path in (self._maybe_handle_save_command, self._maybe_handle_simple_task):
            result = fast_path(state)
            if inspect.isawaitable(result):
                result = await result
            if result is not None:
                return result

        await self._build_plan(state)
        await self._execute_plan_steps(state)
        await self._run_quality_loop(state)
        await self._run_validation(state)
        await self._run_post_validation_fix(state)
        answer = await self._write_report(state)
        await self._store_memory(state, answer)
        return self._build_result(state, answer, score=state.val_score, approved=state.approved)
