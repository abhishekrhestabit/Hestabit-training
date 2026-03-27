import asyncio
import pandas as pd
import os
from typing import List
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage

def get_research_agent(model_client, model_context):
    return AssistantAgent(
        name="researcher",
        model_client=model_client,
        model_context=model_context,
        system_message="You are a data researcher. Analyze provided CSV metrics to identify trends, outliers, and data structures."
    )

def get_summarizer_agent(model_client, model_context):
    return AssistantAgent(
        name="summarizer",
        model_client=model_client,
        model_context=model_context,
        system_message="You are a summarizer. Condense analytical insights into concise, actionable summaries for the user."
    )

def get_answer_agent(model_client, model_context):
    return AssistantAgent(
        name="answerer",
        model_client=model_client,
        model_context=model_context,
        system_message="You are an expert communicator. Answer user questions directly based on the data analysis performed by your team."
    )

def load_csv_data(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} was not found.")
    
    df = pd.read_csv(file_path)
    summary = (
        f"DATASET METADATA:\n"
        f"- Columns: {list(df.columns)}\n"
        f"- Row Count: {len(df)}\n"
        f"- Column Types:\n{df.dtypes.to_string()}\n"
        f"- Descriptive Stats (Sample):\n{df.describe().iloc[[0, 1, 3, 7]].to_string()}"
    )
    return summary

async def main():
    model_client = OllamaChatCompletionClient(
        model="qwen2.5:3b", 
        model_info={"vision": False, "function_calling": True, "json_output": True}
    )

    file_path = input("Enter the path to your CSV file: ").strip()
    try:
        csv_metadata = load_csv_data(file_path)
    except Exception as e:
        print(f"\n[ERROR] Failed to load CSV: {e}")
        return

    system_msg = TextMessage(content=f"You have access to the following CSV metadata:\n{csv_metadata}", source="system")
    
    from autogen_agentchat.base import BufferedChatCompletionContext
    context = BufferedChatCompletionContext(buffer_size=15)
    await context.add_message(system_msg)
    
    researcher = get_research_agent(model_client, context)
    summarizer = get_summarizer_agent(model_client, context)
    answerer = get_answer_agent(model_client, context)

    termination = MaxMessageTermination(max_messages=4)
    team = RoundRobinGroupChat(
        participants=[researcher, summarizer, answerer], 
        termination_condition=termination
    )

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