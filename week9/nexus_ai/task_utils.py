import re


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
