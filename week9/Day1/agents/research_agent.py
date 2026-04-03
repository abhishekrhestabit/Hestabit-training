from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_research_agent(model_client, model_context: BufferedChatCompletionContext | None = None):
    return AssistantAgent(
        name="Research_Agent",
        system_message=(
            "You are a general-purpose researcher. Your task is to extract specific facts, "
            "data points, and relevant information from any context provided in the conversation. "
            "If additional context (such as file data or metadata) is available, use it. "
            "Otherwise, rely on your knowledge to gather and present the requested information. "
            "Focus only on retrieving the requested information without performing analysis or formatting."
        ),
        model_client=model_client,
        model_context=model_context or BufferedChatCompletionContext(buffer_size=10)
    )
