from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_answer_agent(model_client):
    return AssistantAgent(
        name="Answer_Agent",
        system_message=(
            "You are the final answer generator. You have access to the CSV data provided "
            "in the shared team context. Take the analytical summaries provided by the "
            "Summarizer_Agent and format them into a cohesive, user-friendly, and polite "
            "final response. Do not perform any new research. Do not use any markdown "
            "formatting such as #, **, *, or backticks. Write in plain text only, "
            "using simple line breaks and indentation for structure."
        ),
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )