from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_answer_agent(model_client, model_context: BufferedChatCompletionContext | None = None):
    return AssistantAgent(
        name="Answer_Agent",
        system_message=(
            "You are the final answer generator. Take the analytical summaries provided by the "
            "Summarizer_Agent and format them into a cohesive, user-friendly, and polite "
            "final response. If additional context (such as file data) was provided, incorporate it. "
            "Do not perform any new research. Do not use any markdown "
            "formatting such as #, **, *, or backticks. Write in plain text only, "
            "using simple line breaks and indentation for structure."
        ),
        model_client=model_client,
        model_context=model_context or BufferedChatCompletionContext(buffer_size=10)
    )
