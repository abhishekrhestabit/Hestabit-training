"""
day4_pipeline.py
─────────────────────────────────────────────────────────────────
Day 4 — Memory-Augmented Chat

Three memory layers — same philosophy as ChatGPT/Claude memory:
    session_memory  — current conversation window (RAM, resets on exit)
    vector_store    — semantic search over past facts (FAISS, persists)
    long_term.db    — verified facts only, no duplicates (SQLite, persists)

Memory behaviour:
    • Only genuinely new, non-duplicate facts are stored long-term
    • If memory has no answer, the model says so — no hallucination
    • Vector + LTM persist across restarts automatically
    • Session resets on exit (like any chat app)

Commands:  memory | clear | exit
─────────────────────────────────────────────────────────────────
"""

import asyncio, json, re
from pathlib import Path

from autogen_core.models import UserMessage, SystemMessage
from config.model_loader   import get_model_client
from memory.session_memory import SessionMemory
from memory.vector_store   import VectorStore
from memory.long_term      import LongTermMemory


# ── Colours ──────────────────────────────────────────────────────
class C:
    RESET="\033[0m"; BOLD="\033[1m"; CYAN="\033[96m"; GREEN="\033[92m"
    GREY="\033[90m"; PURPLE="\033[35m"

def hdr(t):  print(f"\n{C.BOLD}{C.CYAN}{'─'*55}\n  {t}\n{'─'*55}{C.RESET}")
def ok(t):   print(f"  {C.GREEN}✅ {t}{C.RESET}")
def info(t): print(f"  {C.GREY}{t}{C.RESET}")
def mem(t):  print(f"  {C.PURPLE}🧠 {t}{C.RESET}")


# ── LLM helper ───────────────────────────────────────────────────
async def llm(client, system: str, user: str) -> str:
    r = await client.create(messages=[
        SystemMessage(content=system),
        UserMessage(content=user, source="chat"),
    ])
    c = r.content
    if isinstance(c, list):
        c = " ".join(p.text if hasattr(p, "text") else str(p) for p in c)
    return (c or "").strip()


# ── STEP 1: RECALL ───────────────────────────────────────────────
def recall(query: str,
           session: SessionMemory,
           vector:  VectorStore,
           ltm:     LongTermMemory) -> str:
    """Collect context from all three memory layers."""
    parts = []

    # Session: recent turns in this conversation
    s = session.recall_context()
    if s:
        parts.append(s)

    # Vector: semantically similar past facts/exchanges
    v = vector.recall_context(query)
    if v:
        parts.append(v)

    # Long-term: keyword-matched stored facts
    keyword = query.split()[0] if query else ""
    l = ltm.get_as_context(keyword=keyword, n=3)
    if l:
        parts.append(l)

    return "\n\n".join(parts)


# ── STEP 2: RESPOND ──────────────────────────────────────────────
CHAT_SYS = """\
You are a helpful AI assistant with memory of past conversations.

You will receive the user's message and optionally a [Memory] section
containing facts and past exchanges you have stored about this user.

RULES:
  - If [Memory] contains a direct answer, use it confidently.
  - If [Memory] exists but doesn't answer the question, say so honestly.
  - If there is NO [Memory], say you don't have that information yet —
    NEVER guess or invent personal details like names, ages, or preferences.
  - Be concise and conversational.\
"""

async def respond(client, query: str, memory_context: str) -> str:
    if memory_context:
        prompt = f"{query}\n\n[Memory]\n{memory_context}"
    else:
        prompt = query
    return await llm(client, CHAT_SYS, prompt)


# ── STEP 3: STORE ────────────────────────────────────────────────
# Category tags used by LTM for structured filtering
# Vector store handles "find by meaning" — LTM handles "filter by category"
FACT_FILTER_SYS = """\
You are a memory manager. Decide what is worth storing from this exchange.

ALREADY STORED FACTS:
{existing}

NEW EXCHANGE:
User: {query}
Assistant: {answer}

Extract only facts that are:
  1. NEW — not already in the stored facts above
  2. PERSONAL or FACTUAL — about the user, their preferences, or world facts
  3. REUSABLE — useful for answering future questions

Do NOT store:
  - Duplicates or near-duplicates of existing facts
  - Greetings, acknowledgements ("got it", "noted")
  - Questions (only store answers/facts)

For each fact, assign ONE category tag from:
  personal | preference | work | health | location | knowledge | other

Output a JSON array of objects. Empty array [] if nothing new.
Format: [{{"fact": "...", "tag": "..."}}]
Raw JSON only. No fences.\
"""

async def store(client,
                query:   str,
                answer:  str,
                session: SessionMemory,
                vector:  VectorStore,
                ltm:     LongTermMemory) -> None:
    """
    What each layer stores — and why:

    session  → full conversation turns (current session only, resets on exit)
               Purpose: rolling context window so the model remembers
               what was said earlier in THIS conversation.

    vector   → distilled facts only, no raw Q&A
               Purpose: semantic search — "what do I know that's
               similar to this question?" across ALL sessions.
               Grows slowly, only when genuinely new facts are learned.

    long_term → same facts as vector, stored in SQL for keyword search
               Purpose: structured storage, browsable, deletable.
    """
    # Session: always store both turns (ephemeral, resets on exit)
    session.add_user(query)
    session.add_assistant(answer)

    # Get existing facts to deduplicate against
    existing_facts = ltm.get_recent(n=20)
    existing_text  = "\n".join(f"- {f['fact']}" for f in existing_facts) or "None yet."

    # Ask LLM to extract only genuinely new, non-duplicate facts
    raw = await llm(
        client,
        FACT_FILTER_SYS.format(
            existing=existing_text,
            query=query,
            answer=answer[:400],
        ),
        "Extract new facts:",
    )
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    new_facts = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "fact" in item:
                    new_facts.append({
                        "fact": item["fact"].strip(),
                        "tag":  item.get("tag", "other").strip(),
                    })
                elif isinstance(item, str) and item.strip():
                    # fallback if model returns plain strings
                    new_facts.append({"fact": item.strip(), "tag": "other"})
    except Exception:
        pass

    if new_facts:
        for item in new_facts:
            fact, tag = item["fact"], item["tag"]
            # Vector: embed for semantic search ("find things LIKE this")
            vector.store_fact(fact)
            # LTM: store with category tag for structured filtering
            # ("show me all health facts", "show me all work facts")
            ltm.store(fact, source="fact", tags=[tag])
            mem(f"[{tag}] {fact[:80]}")
    else:
        mem("No new facts to store.")


# ── CLI ──────────────────────────────────────────────────────────
BANNER = """
╔═══════════════════════════════════════════════════════╗
║        DAY 4 — Memory-Augmented Chat                  ║
║                                                       ║
║  Three memory layers active:                          ║
║    🧠 Session memory  (current conversation, RAM)     ║
║    🧠 Vector store    (semantic FAISS, persists)      ║
║    🧠 Long-term DB    (tagged facts, SQLite, persists)║
║                                                       ║
║  Commands:                                            ║
║    memory              — show all stored memory       ║
║    recall <category>   — e.g. recall personal         ║
║    clear               — wipe everything              ║
║    exit                — quit                         ║
╚═══════════════════════════════════════════════════════╝"""


async def chat_loop():
    print(BANNER)
    client  = get_model_client()
    session = SessionMemory(window=10)
    vector  = VectorStore(store_path="memory", top_k=3)
    ltm     = LongTermMemory(db_path="memory/long_term.db")

    print(f"\n  Memory loaded: {session.turn_count} session turns | "
          f"{vector.count} vectors | {ltm.count} facts\n")

    while True:
        try:
            print(f"\n{'─'*55}")
            query = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exiting]"); break

        if not query:
            continue
        if query.lower() in ("exit", "quit", "q", "extit", "exot", "exiy", "ext"):
            print("[Exiting]"); break

        # ── Special commands ──────────────────────────────────
        if query.lower() == "memory":
            hdr("MEMORY STATE")
            session.display()
            vector.display()
            ltm.display()
            print(f"  {session.turn_count} session turns | "
                  f"{vector.count} vectors | {ltm.count} facts")
            continue

        if query.lower().startswith("recall "):
            # Demonstrate LTM's unique capability: filter by category tag
            # e.g. "recall personal" or "recall health" or "recall work"
            tag = query[7:].strip().lower()
            hdr(f"LTM — facts tagged '{tag}'")
            rows = ltm.get_by_source("fact", limit=50)
            tagged = [r for r in rows if tag in (r.get("tags") or "")]
            if tagged:
                for r in tagged:
                    print(f"  • {r['fact']}")
            else:
                print(f"  No facts tagged '{tag}' found.")
            print(f"\n  (Try: recall personal | recall work | recall health | recall preference)")
            continue

        if query.lower() == "clear":
            session.clear(); vector.clear(); ltm.clear()
            ok("All memory cleared."); continue

        # ── Recall ────────────────────────────────────────────
        hdr("MEMORY — recalling")
        context = recall(query, session, vector, ltm)
        if context:
            mem(f"Context ({len(context)} chars):\n"
                f"{context[:350]}{'...' if len(context)>350 else ''}")
        else:
            mem("No relevant memories found.")

        # ── Respond ───────────────────────────────────────────
        answer = await respond(client, query, context)
        print(f"\n{C.BOLD}  Assistant:{C.RESET} {answer}\n")

        # ── Store ─────────────────────────────────────────────
        hdr("MEMORY — storing")
        await store(client, query, answer, session, vector, ltm)
        mem(f"session={session.turn_count} turns | "
            f"vectors={vector.count} | facts={ltm.count}")


if __name__ == "__main__":
    Path("memory").mkdir(exist_ok=True)
    asyncio.run(chat_loop())