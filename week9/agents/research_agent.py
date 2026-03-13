from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_research_agent(model_client):
    return AssistantAgent(
        name="Research_Agent",
        system_message="You are a data researcher. Your only job is to gather raw facts, data, and context about the user's query. Do not format it nicely. Do not answer the user. Just output raw information.",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )