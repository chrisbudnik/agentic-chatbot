from app.agents.dummy_agent import DummyAgent, DummySearchTool, DummyAgentWithError
from app.agents.llm_agent import LLMAgent


# Simple Registry
AGENTS = {
    "default": LLMAgent(tools=[DummySearchTool()]),
    "dummy": DummyAgent(
        name="Dummy Agent",
        description="A simple agent that simulates search.", 
        tools=[DummySearchTool()]
    ),
    "dummy_error": DummyAgentWithError(
        name="Error Agent", 
        description="An agent that always returns an error.", 
        tools=[DummySearchTool()]
    )
}