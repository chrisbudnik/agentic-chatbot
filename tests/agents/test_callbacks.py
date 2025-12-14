import pytest
from app.agents.callbacks import run_callback_with_events
from app.agents.models import AgentEvent, CallbackContext


@pytest.mark.asyncio
async def test_run_callback_async_gen():
	async def cb(context: CallbackContext):
		yield AgentEvent(type="test", content="1")
		yield AgentEvent(type="test", content="2")
		context.modified_input = "modified"

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="test_cb",
	):
		events.append(event)

	# execute_callback, test(1), test(2), execute_callback_result
	assert len(events) == 4
	assert events[1].content == "1"
	assert events[2].content == "2"
	assert ctx.modified_input == "modified"


@pytest.mark.asyncio
async def test_run_callback_return_string():
	async def cb(context: CallbackContext):
		return "new_val"

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="test_cb",
	):
		events.append(event)

	assert ctx.modified_input == "new_val"
	assert events[-1].type == "execute_callback_result"
	assert "new_val" in events[-1].content


@pytest.mark.asyncio
async def test_run_callback_return_list():
	async def cb(context: CallbackContext):
		return [AgentEvent(type="test", content="list")]

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="test_cb",
	):
		events.append(event)

	assert any(e.content == "list" for e in events)


@pytest.mark.asyncio
async def test_run_callback_error():
	async def cb(context: CallbackContext):
		raise ValueError("Oops")

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="test_cb",
	):
		events.append(event)

	error_events = [e for e in events if e.type == "error"]
	assert len(error_events) == 1
	assert "ValueError" in error_events[0].content
