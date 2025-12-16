from app.agents.examples.dummy_agent import (
	DummyAgent,
	DummyAgentWithError,
)
from app.agents.examples.example_tools import DummySearchTool
from app.agents.tools.vertexai_rag_tool import VertexAIRagTool
from app.agents.examples.example_agent import demo_agent
from app.agents.llm_agent import LLMAgent


# Simple Registry
AGENTS = {
	"default": LLMAgent(
		name="LLM Agent",
		description="The default LLM agent.",
		tools=[VertexAIRagTool()],
	),
	"dummy": DummyAgent(
		name="Dummy Agent",
		description="A simple agent that simulates search.",
		tools=[DummySearchTool()],
	),
	"dummy_error": DummyAgentWithError(
		name="Error Agent",
		description="An agent that always returns an error.",
		tools=[DummySearchTool()],
	),
	"demo_agent": demo_agent,
}
