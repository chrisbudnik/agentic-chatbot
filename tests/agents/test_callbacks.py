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


# ============================================================
# NEW TESTS: Sync callbacks, dict returns, tuples, None
# ============================================================


@pytest.mark.asyncio
async def test_run_callback_sync_function():
	"""Sync callback (no async/await) works correctly."""

	def sync_cb(context: CallbackContext):
		# This is a synchronous function, not async
		return "sync_result"

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=sync_cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="sync_test",
	):
		events.append(event)

	# Sync return value should be stored in context
	assert ctx.modified_input == "sync_result"

	# Should have execute_callback start and result events
	assert events[0].type == "execute_callback"
	assert events[-1].type == "execute_callback_result"
	assert "sync_result" in events[-1].content


@pytest.mark.asyncio
async def test_run_callback_returns_dict():
	"""Callback returning a dict stores it in context attribute."""

	async def dict_cb(context: CallbackContext):
		return {"key": "value", "count": 42}

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=dict_cb,
		callback_input={},
		context=ctx,
		context_attr="tool_input",
		callback_type="dict_test",
	):
		events.append(event)

	# Dict should be stored in the specified context attribute
	assert ctx.tool_input == {"key": "value", "count": 42}

	# execute_callback_result should contain the dict representation
	assert events[-1].type == "execute_callback_result"


@pytest.mark.asyncio
async def test_run_callback_returns_tuple_of_events():
	"""Callback returning a tuple of events yields all of them."""

	async def tuple_cb(context: CallbackContext):
		return (
			AgentEvent(type="first", content="Event 1"),
			AgentEvent(type="second", content="Event 2"),
			AgentEvent(type="third", content="Event 3"),
		)

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=tuple_cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="tuple_test",
	):
		events.append(event)

	# All three events from tuple should be yielded
	assert any(e.type == "first" and e.content == "Event 1" for e in events)
	assert any(e.type == "second" and e.content == "Event 2" for e in events)
	assert any(e.type == "third" and e.content == "Event 3" for e in events)

	# Should still have wrapper events
	assert events[0].type == "execute_callback"
	assert events[-1].type == "execute_callback_result"


@pytest.mark.asyncio
async def test_run_callback_none_callback():
	"""callback_fn=None exits early without yielding any events."""

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=None,  # No callback provided
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="none_test",
	):
		events.append(event)

	# Should yield no events when callback is None
	assert len(events) == 0

	# Context should remain unchanged
	assert ctx.modified_input is None


@pytest.mark.asyncio
async def test_run_callback_with_input_params():
	"""Callback receives input parameters correctly."""

	async def input_cb(
		user_input: str, history: list, context: CallbackContext
	):
		context.modified_input = (
			f"Received: {user_input}, history len: {len(history)}"
		)
		return context.modified_input

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=input_cb,
		callback_input={"user_input": "Hello!", "history": [1, 2, 3]},
		context=ctx,
		context_attr="modified_input",
		callback_type="input_test",
	):
		events.append(event)

	# Callback should have received and processed the inputs
	assert ctx.modified_input == "Received: Hello!, history len: 3"


@pytest.mark.asyncio
async def test_run_callback_async_returns_single_event():
	"""Async callback returning a single AgentEvent yields it."""

	async def single_event_cb(context: CallbackContext):
		return AgentEvent(type="single", content="Only one event")

	ctx = CallbackContext()
	events = []
	async for event in run_callback_with_events(
		callback_fn=single_event_cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="single_event_test",
	):
		events.append(event)

	# The single returned event should be yielded
	assert any(
		e.type == "single" and e.content == "Only one event" for e in events
	)


@pytest.mark.asyncio
async def test_run_callback_returns_none_explicitly():
	"""Callback explicitly returning None doesn't set context attribute."""

	async def none_return_cb(context: CallbackContext):
		# Explicitly return None
		return None

	ctx = CallbackContext()
	ctx.modified_input = "original"  # Pre-set value

	events = []
	async for event in run_callback_with_events(
		callback_fn=none_return_cb,
		callback_input={},
		context=ctx,
		context_attr="modified_input",
		callback_type="none_return_test",
	):
		events.append(event)

	# Context attribute should NOT be overwritten with None
	# (the Case 4 check is `elif result is not None`)
	assert ctx.modified_input == "original"
