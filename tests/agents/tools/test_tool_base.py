import pytest
import json
from pydantic import BaseModel
from app.agents.tools.base import BaseTool
from app.agents.models import CallbackContext
from unittest.mock import MagicMock


class InputModel(BaseModel):
	query: str


class MockTool(BaseTool):
	name = "mock_tool"
	description = "A mock tool"
	input_schema = InputModel

	async def run(self, query: str):
		if query == "error":
			raise ValueError("Test Error")
		return f"Result: {query}"


@pytest.mark.asyncio
async def test_tool_schema():
	tool = MockTool()
	schema = tool.schema
	assert "properties" in schema
	assert "query" in schema["properties"]


@pytest.mark.asyncio
async def test_to_openai_tool():
	tool = MockTool()
	oai_tool = tool.to_openai_tool()
	assert oai_tool["type"] == "function"
	assert oai_tool["function"]["name"] == "mock_tool"


def test_parse_tool_args():
	assert BaseTool.parse_tool_args('{"a": 1}') == {"a": 1}
	assert BaseTool.parse_tool_args({"a": 1}) == {"a": 1}
	assert BaseTool.parse_tool_args(None) == {}
	assert BaseTool.parse_tool_args("invalid") == {}


@pytest.mark.asyncio
async def test_execute_success():
	tool = MockTool()
	ctx = CallbackContext()

	# Create a mock tool call object (simulating OpenAI object)
	tool_call = MagicMock()
	tool_call.id = "call_123"
	tool_call.function.name = "mock_tool"
	tool_call.function.arguments = json.dumps({"query": "hello"})

	events = []
	async for event in tool.execute(tool_call, ctx):
		events.append(event)

	assert ctx.tool_result == "Result: hello"
	assert events[-1].type == "tool_result"
	assert events[-1].content == "Result: hello"


@pytest.mark.asyncio
async def test_execute_error():
	tool = MockTool()
	ctx = CallbackContext()

	tool_call = MagicMock()
	tool_call.id = "call_err"
	tool_call.function.name = "mock_tool"
	tool_call.function.arguments = json.dumps({"query": "error"})

	events = []
	async for event in tool.execute(tool_call, ctx):
		events.append(event)

	assert "ValueError" in ctx.tool_result
	# Should catch error and yield error event, then yield tool_result event with error message
	assert any(e.type == "error" for e in events)
	assert events[-1].type == "tool_result"
