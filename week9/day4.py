from __future__ import annotations
import asyncio
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console

from config import describe_active_model, get_model_client
from memory.session_memory import MemorySystem


def _rule(char: str = "=", width: int = 78) -> str: return char * width

def _section(title: str, char: str = "=") -> None:
    print(f"\n{_rule(char)}\n{title}\n{_rule(char)}")

async def build_agent(mem: MemorySystem) -> AssistantAgent:
    
    # Tool for the agent to actively save facts to Vector/SQLite
    async def save_core_fact(fact: str) -> str:
        """Save important user facts, names, or preferences to long-term memory. 
        Argument must be a single, plain string summarizing the fact."""
        await mem.store_fact(fact)
        return f"Fact successfully saved: {fact}"

    return AssistantAgent(
        name="MemoryAgent",
        model_client=get_model_client(),
        tools=[save_core_fact],
        memory=[mem.session, mem.fact_memory],  # Both memory tiers auto-injected
        reflect_on_tool_use=True,  # Forces agent to generate a conversational reply after using a tool
        system_message=(
            "You are an assistant with short and long-term memory. "
            "Context from both is auto-injected. "
            "CRITICAL: If the user reveals a NEW important fact (name, preference, goal), "
            "you MUST call the `save_core_fact` tool to commit it to long-term memory. "
            "DO NOT save facts that are already listed in your 'Relevant long-term facts' context. "
            "Always acknowledge the user naturally after saving their information.\n"
            "JSON FORMATTING RULES: When calling tools, ensure your arguments are valid JSON. "
            "NEVER add a trailing comma or extra closing braces '}'. "
            "Example of a valid tool call argument: {\"fact\": \"User enjoys going to the gym\"}"
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
    print("Type a query, 'stats' to see memory state, or 'exit' to quit.\n" + _rule())

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