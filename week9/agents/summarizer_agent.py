from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_summarizer_agent(model_client, model_context: BufferedChatCompletionContext | None = None):
    """
    Summarizer agent responsible for distilling research data into concise insights.
    The agent expects the research context to be pre-loaded into the shared conversation state
    to avoid redundant token usage.
    """
    return AssistantAgent(
        name="Summarizer_Agent",
        system_message=(
            "You are a summarization specialist. Your role is to take the processed data provided "
            "in the conversation history and distill it into a concise, professional, bulleted summary. "
            "Focus only on key insights and trends. Do not add external information or hallucinate facts."
        ),
        model_client=model_client,
        model_context=model_context or BufferedChatCompletionContext(buffer_size=10)
    )
