from autogen_agentchat.agents import AssistantAgent

def get_worker(name, role_focus, model_client):
    return AssistantAgent(
        name=name,
        system_message=f"""You are a specialized worker focusing exclusively on: {role_focus}. 
Look at the Planner's output in the chat history and execute ONLY your specific portion of the plan. 
Keep your response concise. Do not do the other worker's job.""",
        model_client=model_client
    )

def get_reflection_agent(model_client):
    return AssistantAgent(
        name="Reflection_Agent",
        system_message="""You are the Reflection Agent. Review the outputs from Worker_1_Tech and Worker_2_Biz. 
Synthesize their findings into a single, cohesive master draft. Resolve any contradictions.""",
        model_client=model_client
    )