from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_answer_agent(model_client):
    return AssistantAgent(
        name="Answer_Agent",
        system_message="You are the final answer generator. Take the bulleted summary from the Summarizer_Agent and format it into a cohesive, user-friendly, and polite final response. Do not perform any new research.",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )