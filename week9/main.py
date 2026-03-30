import asyncio
import os
import pandas as pd

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import UserMessage

from agents.answer_agent import get_answer_agent
from agents.research_agent import get_research_agent
from agents.summarizer_agent import get_summarizer_agent
from config import describe_active_model, get_model_client

def load_csv_data(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} was not found.")

    df = pd.read_csv(file_path)
    describe_frame = df.describe(include="all").fillna("N/A").head(8)
    summary = (
        f"DATASET METADATA:\n"
        f"- Columns: {list(df.columns)}\n"
        f"- Row Count: {len(df)}\n"
        f"- Column Types:\n{df.dtypes.to_string()}\n"
        f"- Descriptive Stats (Sample):\n{describe_frame.to_string()}"
    )
    return summary


async def main():
    model_client = get_model_client()

    file_path = input("Enter the path to your CSV file: ").strip()
    try:
        csv_metadata = load_csv_data(file_path)
    except Exception as e:
        print(f"\n[ERROR] Failed to load CSV: {e}")
        return

    dataset_context = UserMessage(
        content=f"You have access to the following CSV metadata:\n{csv_metadata}",
        source="dataset",
    )

    context = BufferedChatCompletionContext(buffer_size=10)
    await context.add_message(dataset_context)

    researcher = get_research_agent(model_client, context)
    summarizer = get_summarizer_agent(model_client, context)
    answerer = get_answer_agent(model_client, context)

    termination = MaxMessageTermination(max_messages=4)
    team = RoundRobinGroupChat(
        participants=[researcher, summarizer, answerer], 
        termination_condition=termination
    )

    print(f"\n[SYSTEM] Active model: {describe_active_model()}")
    print("\n[SYSTEM] CSV metadata ingested into agent context.")

    while True:
        user_query = input("\n[USER] Ask a question about the data (or 'exit'): ")
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
