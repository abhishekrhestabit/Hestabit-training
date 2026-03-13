import asyncio
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient

from orchestrator.planner import get_planner
from agents.worker_agent import get_worker, get_reflection_agent
from agents.validator import get_validator

async def main():
    # 1. Connect to Qwen 2.5 3B
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

    # 2. Instantiate all 5 agents
    planner = get_planner(model_client)
    worker_1 = get_worker("Worker_1_Tech", "Technical Architecture", model_client)
    worker_2 = get_worker("Worker_2_Biz", "Business Strategy", model_client)
    reflection = get_reflection_agent(model_client)
    validator = get_validator(model_client)

    # 3. Define the DAG State Machine (Chain of Command)
    def custom_router(messages):
        if not messages:
            return "Planner"
            
        last_speaker = messages[-1].source
        
        # The Execution Tree
        if last_speaker == "user":
            return "Planner"
        elif last_speaker == "Planner":
            return "Worker_1_Tech"
        elif last_speaker == "Worker_1_Tech":
            return "Worker_2_Biz"
        elif last_speaker == "Worker_2_Biz":
            return "Reflection_Agent"
        elif last_speaker == "Reflection_Agent":
            return "Validator_Agent"
        else:
            return None # Terminate the flow

    # 4. Create the Team using the custom router
    termination = MaxMessageTermination(max_messages=6)
    team = SelectorGroupChat(
        participants=[planner, worker_1, worker_2, reflection, validator],
        selector_func=custom_router,
        termination_condition=termination
    )

    # 5. Execute the Workflow
    user_query = "Plan a basic SaaS application for AI-driven fitness tracking."
    print("==================================================")
    print(f"DAY 2 TASK: {user_query}")
    print("==================================================\n")
    
    result = await team.run(task=user_query)
    
    for msg in result.messages:
        if msg.source != "user":
            print(f"\n[{msg.source.upper()}] says:\n{msg.content}\n")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())