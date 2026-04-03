import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_core.model_context import BufferedChatCompletionContext

from agents.answer_agent import get_answer_agent
from agents.research_agent import get_research_agent
from agents.summarizer_agent import get_summarizer_agent
from config import describe_active_model, get_model_client


async def main():
    model_client = get_model_client()

    context = BufferedChatCompletionContext(buffer_size=10)

    researcher = get_research_agent(model_client, context)
    summarizer = get_summarizer_agent(model_client, context)
    answerer = get_answer_agent(model_client, context)

    termination = MaxMessageTermination(max_messages=4)
    team = RoundRobinGroupChat(
        participants=[researcher, summarizer, answerer],
        termination_condition=termination
    )

    print(f"\n[SYSTEM] Active model: {describe_active_model()}")
    print("[SYSTEM] Ready. Ask any question.\n")

    while True:
        user_query = input("\n[USER] Ask a question (or 'exit'): ").strip()
        if not user_query:
            continue
        if user_query.lower() in ['exit', 'quit']:
            break

        try:
            result = await team.run(task=user_query)
            for msg in result.messages:
                if msg.source != "user" and msg.source != "system":
                    print(f"\n[{msg.source.upper()}] says:\n{msg.content}\n")
        except Exception as e:
            print(f"\n[ERROR] Team processing failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
