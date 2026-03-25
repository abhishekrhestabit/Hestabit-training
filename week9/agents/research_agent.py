from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_research_agent(model_client):
    return AssistantAgent(
        name="Research_Agent",
        system_message="""You are a data researcher. Your task is to extract specific facts 
        and raw data points from the provided CSV context. 
        Focus only on retrieving the requested information without performing analysis or formatting.""",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )