import pytest
from unittest.mock import MagicMock, AsyncMock
from app.agents.llm_agent import LLMAgent
from app.agents.tools.base import BaseTool


# Mock tool
class SimpleTool(BaseTool):
	name = "simple_search"
	description = "search"

	async def run(self, query):
		return "42"


@pytest.mark.asyncio
async def test_llm_agent_simple_answer():
	agent = LLMAgent(name="TestLLM", description="test")

	# Mock the client
	mock_response = MagicMock()
	mock_response.choices = [
		MagicMock(message=MagicMock(content="Hello", tool_calls=None))
	]

	agent.client = AsyncMock()
	agent.client.chat.completions.create.return_value = mock_response

	events = []
	async for event in agent.process_turn([], "Hi"):
		events.append(event)

	# Expect: thought(history), answer("Hello")
	assert any(e.type == "answer" and e.content == "Hello" for e in events)


@pytest.mark.asyncio
async def test_llm_agent_tool_use_loop():
	# Scenario:
	# 1. User says "Calculate"
	# 2. LLM calls tool "calc"
	# 3. Tool results "100"
	# 4. LLM sees "100" and answers "The answer is 100"

	agent = LLMAgent(name="ToolAgent", description="test", tools=[SimpleTool()])
	agent.client = AsyncMock()

	# Response 1: Call Tool
	tool_call = MagicMock()
	tool_call.id = "call_1"
	tool_call.function.name = "simple_search"
	tool_call.function.arguments = '{"query": "math"}'

	msg1 = MagicMock(content=None, tool_calls=[tool_call])
	resp1 = MagicMock()
	resp1.choices = [MagicMock(message=msg1)]

	# Response 2: Final Answer
	msg2 = MagicMock(content="The answer is 42", tool_calls=None)
	resp2 = MagicMock()
	resp2.choices = [MagicMock(message=msg2)]

	# Setup side_effect for multiple calls
	agent.client.chat.completions.create.side_effect = [resp1, resp2]

	events = []
	async for event in agent.process_turn([], "Calculate"):
		events.append(event)

	# Checks:
	# - tool_call event
	# - tool_result event (content should be 42)
	# - answer event (The answer is 42)

	tool_calls = [e for e in events if e.type == "tool_call"]
	tool_results = [e for e in events if e.type == "tool_result"]
	answers = [e for e in events if e.type == "answer"]

	assert len(tool_calls) == 1
	assert tool_calls[0].tool_name == "simple_search"

	assert len(tool_results) == 1
	assert tool_results[0].content == "42"

	assert len(answers) == 1
	assert answers[0].content == "The answer is 42"
