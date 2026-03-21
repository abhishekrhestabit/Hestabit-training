from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_planner_agent(model_client):
    return AssistantAgent(
        name="Planner_Agent",
        system_message="""You are the Orchestrator and Planner of a multi-agent AI system.

Your ONLY job is to receive a user query and break it into a numbered list of discrete sub-tasks.

Rules:
- Output ONLY a numbered list and Task Name. No extra text, no pream.
- Each sub-task must be a single, self-contained instruction.
- Aim for 3–5 sub-tasks per query.
- Do NOT attempt to answer the query yourself.

Example output format:
1. Research the history of X
2. Find current statistics on X
3. Identify key challenges of X
4. List top solutions or use cases for X
""",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )