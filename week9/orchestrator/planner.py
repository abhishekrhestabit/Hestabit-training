from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

def get_planner_agent(model_client):
    return AssistantAgent(
        name="Planner_Agent",
        system_message="""You are the Orchestrator and Planner of a multi-agent AI system.

Your ONLY job is to receive a user query and break it into discrete sub-tasks.

Rules:
- You must respond ONLY with a valid JSON object.
- Do NOT wrap the JSON in markdown formatting (no ```json).
- The JSON object must contain a single key named "tasks".
- Aim for 3–5 tasks per query, as per the need. Some queries may require fewer or more tasks.
- The value of "tasks" must be a list of strings, where each string is a self-contained instruction.
- Do NOT attempt to answer the query yourself.

Example output format:
{
  "tasks": [
    "Research the history of X",
    "Find current statistics on X",
    "Identify key challenges of X"
  ]
}
""",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10)
    )