import asyncio
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient

from agents.research_agent import get_research_agent
from agents.summarizer_agent import get_summarizer_agent
from agents.answer_agent import get_answer_agent

async def main():
    # 1. Instantiate the native Ollama client
    model_client = OllamaChatCompletionClient(
        model="qwen2.5:3b", 
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": True
        }
    )

    # 2. Instantiate the Agents 
    # (Remember, your agents should have model_context=BufferedChatCompletionContext(buffer_size=10) in their files!)
    researcher = get_research_agent(model_client)
    summarizer = get_summarizer_agent(model_client)
    answerer = get_answer_agent(model_client)

    # 3. Create the Sequential Pipeline
    # MaxMessageTermination(max_messages=4) ensures the loop stops after exactly:
    # 1. User -> 2. Researcher -> 3. Summarizer -> 4. Answerer
    termination = MaxMessageTermination(max_messages=4)
    team = RoundRobinGroupChat(
        participants=[researcher, summarizer, answerer], 
        termination_condition=termination
    )

    print("==================================================")
    print("NEXUS AI - DAY 1 PIPELINE ONLINE")
    print("Type 'exit' or 'quit' to shut down the system.")
    print("==================================================\n")

    # 4. The Live CLI Loop
    while True:
        # Get live input from the user
        user_query = input("\n[USER] Enter your query: ")
        
        # Check if the user wants to quit
        if user_query.lower() in ['exit', 'quit']:
            print("\nShutting down pipeline...")
            break
            
        print("\n" + "-" * 50)
        
        # Run the team workflow for this specific query
        result = await team.run(task=user_query)
        
        # Print only the agent responses from THIS turn (skipping the user's own prompt)
        for msg in result.messages:
            # We don't need to print the user's message again, only the agents
            if msg.source != "user":
                print(f"\n[{msg.source.upper()}] says:\n{msg.content}\n")
                print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())