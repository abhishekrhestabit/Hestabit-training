from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_worker_agent(model_client, worker_id: int):
    return AssistantAgent(
        name=f"Worker_Agent_{worker_id}",
        system_message=f"""You are Worker Agent #{worker_id} in a multi-agent pipeline.

You will receive a single sub-task. Your job is to execute ONLY that sub-task thoroughly.

Rules:
- Focus strictly on the assigned sub-task.
- Provide detailed, factual output.
- Do NOT summarize other tasks or answer the overall query.
- Label your output clearly: start with "WORKER {worker_id} OUTPUT:"
""",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )