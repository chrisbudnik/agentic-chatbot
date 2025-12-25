from app.agents.examples.dummy_agent import (
	DummyAgent,
	DummyAgentWithError,
)
from app.agents.examples.example_tools import DummySearchTool
from app.agents.tools.vertexai_search_tool import VertexAISearchTool
from app.agents.tools.vertexai_rag_engine_tool import VertexAIRagEngineTool
from app.agents.examples.example_agent import demo_agent
from app.agents.llm_agent import LLMAgent


# Simple Registry
AGENTS = {
	"default": LLMAgent(
		name="LLM Agent (GCP AI Application)",
		description="LLM agent using GCP AI Application search tool.",
		system_prompt="You are a helpful assistant. Answer questions based using search tools.",
		tools=[VertexAISearchTool()],
	),
	"rag_engine": LLMAgent(
		name="LLM Agent (Rag Engine)",
		description="LLM agent using Vertex AI Rag Engine search tool.",
		system_prompt="You are a helpful assistant. Answer questions based using search tools.",
		tools=[VertexAIRagEngineTool()],
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
