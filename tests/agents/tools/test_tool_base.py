import pytest
import json
from pydantic import BaseModel
from app.agents.tools.base import BaseTool
from app.agents.models import CallbackContext, AgentEvent
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


class StreamingTool(BaseTool):
	name = "streaming_tool"
	description = "A tool that yields events"
	input_schema = InputModel

	async def run(self, context: CallbackContext, query: str):
		yield AgentEvent(type="thought", content=f"working on {query}")
		yield AgentEvent(type="tool_result", content=f"partial {query}")
		context.tool_result = f"Result: {query}"


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


@pytest.mark.asyncio
async def test_execute_streaming_tool_yields_events():
	tool = StreamingTool()
	ctx = CallbackContext()

	tool_call = MagicMock()
	tool_call.id = "call_stream"
	tool_call.function.name = "streaming_tool"
	tool_call.function.arguments = json.dumps({"query": "hello"})

	events = []
	async for event in tool.execute(tool_call, ctx):
		events.append(event)

	# streamed events should be present
	assert any(
		e.type == "thought" and e.content == "working on hello" for e in events
	)
	assert any(
		e.type == "tool_result" and e.content == "partial hello" for e in events
	)

	# final tool_result event emitted by BaseTool.execute should match context.tool_result
	assert ctx.tool_result == "Result: hello"
	assert events[-1].type == "tool_result"
	assert events[-1].content == "Result: hello"


# ============================================================
# NEW TESTS: Callbacks, Schema, and Edge Cases
# ============================================================


class ToolWithCallbacks(BaseTool):
	"""Tool that supports before/after callbacks for testing."""

	name = "callback_tool"
	description = "A tool with callbacks"
	input_schema = InputModel

	async def run(self, query: str):
		return f"Processed: {query}"


class NoSchemaTool(BaseTool):
	"""Tool without an input schema."""

	name = "no_schema_tool"
	description = "A tool without input schema"
	input_schema = None

	async def run(self, **kwargs):
		return f"Got kwargs: {kwargs}"


@pytest.mark.asyncio
async def test_tool_with_before_callback_modifies_input():
	"""Before callback can modify tool arguments before execution."""

	async def before_cb(tool_args: dict, context: CallbackContext):
		# Modify the query before tool runs
		modified_args = {"query": f"modified_{tool_args['query']}"}
		context.tool_input = modified_args
		yield AgentEvent(type="callback", content="Input modified")

	tool = ToolWithCallbacks(before_tool_callback=before_cb)
	ctx = CallbackContext()

	tool_call = MagicMock()
	tool_call.id = "call_before"
	tool_call.function.name = "callback_tool"
	tool_call.function.arguments = json.dumps({"query": "original"})

	events = []
	async for event in tool.execute(tool_call, ctx):
		events.append(event)

	# The tool should have received modified args
	assert ctx.tool_result == "Processed: modified_original"
	assert any(e.type == "callback" and "modified" in e.content for e in events)


@pytest.mark.asyncio
async def test_tool_with_after_callback_modifies_result():
	"""After callback can modify tool result after execution."""

	async def after_cb(tool_result: str, context: CallbackContext):
		# Modify the result after tool runs
		context.tool_result = f"{tool_result} [VERIFIED]"
		yield AgentEvent(type="callback", content="Result verified")

	tool = ToolWithCallbacks(after_tool_callback=after_cb)
	ctx = CallbackContext()

	tool_call = MagicMock()
	tool_call.id = "call_after"
	tool_call.function.name = "callback_tool"
	tool_call.function.arguments = json.dumps({"query": "test"})

	events = []
	async for event in tool.execute(tool_call, ctx):
		events.append(event)

	# The final result should be modified by after callback
	assert "[VERIFIED]" in ctx.tool_result
	assert any(e.type == "callback" and "verified" in e.content for e in events)

	# Final tool_result event should have the modified content
	final_result_event = events[-1]
	assert final_result_event.type == "tool_result"
	assert "[VERIFIED]" in final_result_event.content


@pytest.mark.asyncio
async def test_tool_without_input_schema():
	"""Tool with input_schema = None should return empty schema."""
	tool = NoSchemaTool()

	# Schema should be empty dict
	assert tool.schema == {}

	# to_openai_tool should still work
	oai_tool = tool.to_openai_tool()
	assert oai_tool["type"] == "function"
	assert oai_tool["function"]["name"] == "no_schema_tool"
	assert oai_tool["function"]["parameters"] == {}

	# Execution should still work
	ctx = CallbackContext()
	tool_call = MagicMock()
	tool_call.id = "call_no_schema"
	tool_call.function.name = "no_schema_tool"
	tool_call.function.arguments = json.dumps({"key": "value"})

	events = []
	async for event in tool.execute(tool_call, ctx):
		events.append(event)

	assert "Got kwargs" in ctx.tool_result
	assert events[-1].type == "tool_result"


def test_build_tool_result_message():
	"""Static helper produces correct OpenAI tool result message format."""
	result = BaseTool.build_tool_result_message(
		tool_call_id="call_xyz789",
		tool_name="my_search",
		result="Found 5 documents.",
	)

	assert result == {
		"role": "tool",
		"tool_call_id": "call_xyz789",
		"name": "my_search",
		"content": "Found 5 documents.",
	}


def test_build_tool_result_message_with_empty_result():
	"""build_tool_result_message handles empty result string."""
	result = BaseTool.build_tool_result_message(
		tool_call_id="call_empty",
		tool_name="empty_tool",
		result="",
	)

	assert result["role"] == "tool"
	assert result["content"] == ""


@pytest.mark.asyncio
async def test_tool_run_invalid_non_dict_args():
	"""Tool execution should handle non-dict args gracefully with error."""
	tool = MockTool()
	ctx = CallbackContext()

	# Directly test run_tool_and_parse_output with invalid args
	events = []
	async for event in tool.run_tool_and_parse_output(
		effective_args="not a dict",  # Invalid - should be dict
		context=ctx,
	):
		events.append(event)

	# Should yield an error event
	error_events = [e for e in events if e.type == "error"]
	assert len(error_events) == 1
	assert "dict" in error_events[0].content.lower()

	# Error should be stored in context
	assert "dict" in ctx.tool_result.lower()


@pytest.mark.asyncio
async def test_tool_run_invalid_list_args():
	"""Tool execution should handle list args (another non-dict type)."""
	tool = MockTool()
	ctx = CallbackContext()

	events = []
	async for event in tool.run_tool_and_parse_output(
		effective_args=["not", "a", "dict"],
		context=ctx,
	):
		events.append(event)

	error_events = [e for e in events if e.type == "error"]
	assert len(error_events) == 1
	assert "list" in error_events[0].content.lower()
