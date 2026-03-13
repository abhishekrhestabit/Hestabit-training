from autogen_agentchat.agents import AssistantAgent

def get_validator(model_client):
    return AssistantAgent(
        name="Validator_Agent",
        system_message="""You are the final Validator. Check the Reflection Agent's draft for logical errors or missing information. 
Output the FINAL, polished answer. Do not add new facts.""",
        model_client=model_client
    )