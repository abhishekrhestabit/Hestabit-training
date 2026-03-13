from autogen_agentchat.agents import AssistantAgent

def get_planner(model_client):
    return AssistantAgent(
        name="Planner",
        system_message="""You are the master Planner. Break the user's query into two exact tasks:
1. Technical architecture
2. Business strategy
Output the plan clearly. Do not execute the tasks yourself.""",
        model_client=model_client
    )