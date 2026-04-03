from __future__ import annotations
import asyncio
import sys
from datetime import date

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console

from config import describe_active_model, get_model_client
from memory.session_memory import MemorySystem


def _rule(char: str = "=", width: int = 78) -> str: return char * width

def _section(title: str, char: str = "=") -> None:
    print(f"\n{_rule(char)}\n{title}\n{_rule(char)}")

async def build_agent(mem: MemorySystem) -> AssistantAgent:
    
    # Tool for the agent to actively save facts to Vector/SQLite
    async def save_core_fact(fact: str, category: str) -> str:
        """Save important user facts, names, or preferences to long-term memory.
        Args:
            fact: A single, plain string summarizing the fact.
            category: One of: 'personal', 'preference', 'work', 'health', 'hobby', 'goal', 'general'.
        """
        await mem.store_fact(fact, category=category)
        return f"Fact successfully saved: {fact} [category: {category}]"

    # Tool to retrieve facts stored on a specific date
    async def get_facts_by_date(date_str: str) -> str:
        """Retrieve all facts/conversations stored on a given date.
        Argument must be a date string in YYYY-MM-DD format (e.g. '2026-04-03').
        Use this when the user asks about past conversations or interactions on a specific day."""
        facts = mem.long_term.get_facts_by_date(date_str)
        if not facts:
            return f"No facts or conversations found for {date_str}."
        lines = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
        return f"Facts/conversations from {date_str}:\n{lines}"

    # Tool to retrieve facts by category
    async def get_facts_by_category(category: str) -> str:
        """Retrieve all facts stored under a specific category.
        Argument must be one of: 'personal', 'preference', 'work', 'health', 'hobby', 'goal', 'general'.
        Use this when the user asks about a specific topic area of their stored information."""
        facts = mem.long_term.search_by_category(category)
        if not facts:
            return f"No facts found in category '{category}'."
        lines = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
        return f"Facts in category '{category}':\n{lines}"

    return AssistantAgent(
        name="MemoryAgent",
        model_client=get_model_client(),
        tools=[save_core_fact, get_facts_by_date, get_facts_by_category],
        memory=[mem.session, mem.fact_memory],  # Both memory tiers auto-injected
        reflect_on_tool_use=True,  # Forces agent to generate a conversational reply after using a tool
        system_message=(
            "You are an assistant with short and long-term memory. "
            "Context from both is auto-injected. "
            "CRITICAL: If the user reveals NEW important facts (name, preference, goal, age, etc.), "
            "you MUST call `save_core_fact` ONCE PER FACT. Break compound statements into individual "
            "atomic facts. For example, if a user shares multiple pieces of information in one message, "
            "you MUST make a SEPARATE `save_core_fact` call for each distinct piece of information, "
            "each with its own appropriate category. "
            "NEVER bundle multiple facts into a single save_core_fact call. "
            "When saving, choose the best category from: 'personal', 'preference', 'work', "
            "'health', 'hobby', 'goal', 'general'. "
            "DO NOT save facts that are already listed in your 'Relevant long-term facts' context. "
            "Always acknowledge the user naturally after saving their information.\n"
            f"Today's date is {date.today().isoformat()}. "
            "When the user asks about past conversations, interactions, or what was discussed on a "
            "specific day (including 'today'), call the `get_facts_by_date` tool with the appropriate "
            "YYYY-MM-DD date string to retrieve the stored facts for that date.\n"
            "When the user asks about a specific topic (e.g. 'what are my hobbies?', 'what do I do for work?'), "
            "or asks broad questions like 'tell me about myself', 'what do you know about me?', "
            "'list everything you remember', you MUST call `get_facts_by_category` for each relevant "
            "category to retrieve the COMPLETE set of facts from long-term storage. "
            "The auto-injected context only shows a few top matches — use the tool to get the full picture.\n"
            "JSON FORMATTING RULES: When calling tools, ensure your arguments are valid JSON. "
            "NEVER add a trailing comma or extra closing braces '}'. "
            "Example of a valid tool call argument: {\"fact\": \"User enjoys going to the gym\", \"category\": \"health\"}"
        ),
    )

async def run_turn(agent: AssistantAgent, mem: MemorySystem, query: str) -> None:
    _section("RUN", "-")
    
    try:
        result = await Console(agent.run_stream(task=query), output_stats=False)
        
        await mem.store_turn("user", query)
        
        # Extract only the textual agent response to avoid crashing session on tool calls
        last_msg = next((m.content for m in reversed(result.messages) if isinstance(m.content, str)), "")
        if last_msg:
            await mem.store_turn("agent", last_msg)
            
    except Exception as e:
        print(f"\n[!] Model API Error (likely a JSON formatting glitch): {e}")
        print("[!] The system caught the error. Your message is in short-term memory.")
        print("[!] Just say 'hi' or continue the conversation to let the agent try saving again.")

    print(_rule("-"))

def _print_banner() -> None:
    _section("DAY 4  MEMORY SYSTEMS")
    print(f"Active model : {describe_active_model()}")
    print("Memory tiers : session (in-process) | vector FAISS | long-term SQLite")
    print("Type a query, 'stats' for memory state, 'clear' to wipe memory, or 'exit' to quit.\n" + _rule())

async def interactive_cli() -> None:
    _print_banner()
    mem   = MemorySystem()
    agent = await build_agent(mem)

    while True:
        try: query = input("\n[USER] ").strip()
        except (EOFError, KeyboardInterrupt): break
        
        if not query: continue
        if query.lower() in {"exit", "quit"}: break
        if query.lower() == "stats":
            print(mem.stats())
            continue
        if query.lower() == "clear":
            await mem.clear()
            print("[SYSTEM] All memory cleared (session + vector + long-term).")
            print(mem.stats())
            continue

        await run_turn(agent, mem, query)

    print("\nMemory stats at exit:", mem.stats())

async def main() -> None:
    if len(sys.argv) > 1:
        mem, query = MemorySystem(), " ".join(sys.argv[1:])
        agent = await build_agent(mem)
        await run_turn(agent, mem, query)
        return
    await interactive_cli()

if __name__ == "__main__":
    asyncio.run(main())