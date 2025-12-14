from app.agents.llm_agent import LLMAgent
from app.agents.examples.example_tools import DummySearchTool
from app.agents.examples.example_callbacks import (
    example_before_agent_callback,
    example_after_agent_callback,
    example_before_tool_callback,
    example_after_tool_callback,
)

search_tool = DummySearchTool(
    before_tool_callback=example_before_tool_callback,
    after_tool_callback=example_after_tool_callback
)

demo_agent = LLMAgent(
    name="Demo Agent",
    description="An example agent that uses a dummy search tool with all possible callbacks.",
    model="gpt-4.1",
    tools=[search_tool],
    before_agent_callback=example_before_agent_callback,
    after_agent_callback=example_after_agent_callback
)
