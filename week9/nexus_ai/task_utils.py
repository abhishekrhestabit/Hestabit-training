import json
import re


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

COMPACT_CONTEXT_AGENTS = {
    "Planner": {"Planner", "Researcher", "Coder", "Analyst", "Critic", "Validator", "Optimizer"},
    "Researcher": {"Researcher", "Analyst", "Validator"},
    "Coder": {"Researcher", "Analyst", "Coder", "Critic", "Validator"},
    "Analyst": {"Researcher", "Coder", "Analyst", "Validator"},
    "Critic": {"Researcher", "Coder", "Analyst", "Optimizer", "Validator"},
    "Optimizer": {"Coder", "Analyst", "Critic", "Validator"},
    "Validator": {"Researcher", "Coder", "Analyst", "Critic", "Optimizer"},
}

COMPACT_CONTEXT_LIMITS = {
    "Planner": 4,
    "Researcher": 3,
    "Coder": 4,
    "Analyst": 4,
    "Critic": 5,
    "Optimizer": 4,
    "Validator": 6,
}


def is_simple_task(task: str) -> bool:
    lowered = task.strip().lower()
    complex_signals = [
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
    if any(signal in lowered for signal in complex_signals):
        return False

    simple_patterns = [
        r"^(hi|hello|hey|howdy|sup|yo)\b",
        r"^(thanks|thank you|thx|ty|ok|okay|got it|noted|sure|cool|great)\b",
        r"^(bye|goodbye|see you|cya)\b",
        r"^my name is\b",
        r"^i am\b",
        r"^i'm\b",
        r"^do you remember\b",
        r"^what did we\b",
        r"^what is my\b",
        r"^who am i\b",
        r"^how are you\b",
        r"^what can you do\b",
        r"^tell me about yourself\b",
        r"^nice\b",
        r"^sounds good\b",
        r"^got it\b",
        r"^perfect\b",
        r"^awesome\b",
    ]
    if any(re.match(pattern, lowered) for pattern in simple_patterns):
        return True

    return len(lowered.split()) <= 5


def needs_explicit_research(task: str) -> bool:
    lowered = task.lower()
    signals = [
        "research", "search", "find", "latest", "current", "recent",
        "news", "compare", "comparison", "documentation", "docs",
        "reference", "best", "top ", "who is", "what happened",
        "trend", "trends", "state of",
    ]
    return any(signal in lowered for signal in signals)


def is_local_build_task(task: str) -> bool:
    lowered = task.lower()
    signals = [
        "backend", "api", "crud", "fastapi", "flask", "sqlalchemy",
        "database", "schema", "route", "routes", "endpoint", "endpoints",
        "todo", "to do", "auth", "authentication", "authorization",
        "server", "application", "system", "implement", "build", "generate",
        "write code", "create code",
    ]
    return any(signal in lowered for signal in signals)


def slugify_task(task: str, max_words: int = 12, max_chars: int = 72) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_")
    words = [word for word in cleaned.split("_") if word][:max_words]
    slug = "_".join(words) or "task"
    return slug[:max_chars].strip("_") or "task"


def stringify_output(output) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, indent=2, ensure_ascii=False)
    except Exception:
        return str(output)


def combine_context(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def append_context_block(context: str, label: str, output) -> str:
    block = f"── {label} ──\n{stringify_output(output)}"
    return f"{context}\n\n{block}".strip() if context else block


def agent_base_name(agent_name: str) -> str:
    return agent_name.split(" (", 1)[0]


def detect_save_target(text: str) -> str | None:
    filename = re.search(r"[\w./\-]+\.(?:md|txt|py|json|yaml|yml|html|csv)", text, re.I)
    if not filename:
        return None

    lowered = text.lower()
    target = filename.group(0).lower()
    explicit_patterns = [
        r"\bsave\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(target),
        r"\bstore\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(target),
        r"\bexport\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(target),
        r"\bdump\b.{0,80}\b(?:to|as|in)\b.{0,80}" + re.escape(target),
        r"\bwrite\b.{0,80}\b(?:to|into|in|as)\b.{0,80}" + re.escape(target),
        r"\bput\b.{0,80}\b(?:to|into|in)\b.{0,80}" + re.escape(target),
        r"\b" + re.escape(target) + r"\b.{0,40}\b(?:save|store|export|dump)\b",
    ]
    if not any(re.search(pattern, lowered, re.DOTALL) for pattern in explicit_patterns):
        return None

    ref_words = [
        "this", "it", "that", "the report", "the answer",
        "the analysis", "the above", "previous", "last",
        "generated", "findings", "result", "content", "there",
    ]
    return filename.group(0) if any(word in lowered for word in ref_words) else None


def trim_text(text: str, max_chars: int = 1200) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 32
    return text[:head].rstrip() + f"\n...[trimmed {len(text) - max_chars} chars]...\n" + text[-tail:].lstrip()


def collect_file_refs(base_context: str, context: str, trace: list[dict]) -> list[str]:
    pool = [base_context, context]
    pool.extend(stringify_output(item.get("output", "")) for item in trace)
    refs = set()
    for chunk in pool:
        refs.update(FILE_REF_PATTERN.findall(chunk or ""))
        refs.update(re.findall(r"(?:Created|Updated|Wrote|Generated)\s+([\w./\-]+\.\w+)", chunk or "", re.I))
    return sorted(refs)[:20]


def should_use_full_context(agent_name: str, task: str, instruction: str, full_context: str) -> bool:
    if len(full_context) <= 5000:
        return True
    combined = f"{task}\n{instruction}".lower()
    if any(signal in combined for signal in FOLLOWUP_CONTEXT_SIGNALS):
        return True
    if agent_name == "Coder" and any(signal in combined for signal in ["integrate", "merge", "combine", "refactor", "extend"]):
        return True
    return False


def build_agent_context(
    *,
    base_context: str,
    context: str,
    trace: list[dict],
    agent_name: str,
    task: str,
    instruction: str,
) -> str:
    full_context = combine_context(base_context, context)
    if not full_context:
        return ""
    if should_use_full_context(agent_name, task, instruction, full_context):
        return full_context

    selected = [
        item for item in trace
        if agent_base_name(item.get("agent", "")) in COMPACT_CONTEXT_AGENTS.get(agent_name, set())
    ][-COMPACT_CONTEXT_LIMITS.get(agent_name, 4):]

    parts = [base_context.strip()] if base_context else []
    refs = collect_file_refs(base_context, context, trace)
    if refs:
        parts.append("── Referenced files ──\n" + "\n".join(refs))
    for item in selected:
        label = item.get("agent", "Agent")
        body = trim_text(stringify_output(item.get("output", "")), max_chars=1400)
        parts.append(f"── {label} ──\n{body}")
    compact = "\n\n".join(part for part in parts if part)
    return compact or full_context
