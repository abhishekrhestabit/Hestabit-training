from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_summarizer_agent(model_client):
    return AssistantAgent(
        name="Summarizer_Agent",
        system_message="You are a summarization specialist. Take the raw data provided by the Research_Agent and distill it into a concise, bulleted summary. Drop unnecessary fluff. Do not add new information.",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )