from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_summarizer_agent(model_client, model_context: BufferedChatCompletionContext | None = None):
   
    return AssistantAgent(
        name="Summarizer_Agent",
        system_message=(
            "You are a summarization specialist. Your role is to take the information provided "
            "in the conversation history and distill it into a concise, professional, bulleted summary. "
            "Focus only on key insights and relevant points. Do not add external information or hallucinate facts."
        ),
        model_client=model_client,
        model_context=model_context or BufferedChatCompletionContext(buffer_size=10)
    )
