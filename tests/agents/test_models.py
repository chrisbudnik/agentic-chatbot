from app.agents.models import AgentEvent, CallbackContext


def test_agent_event_defaults():
	event = AgentEvent(type="test", content="content")
	assert event.type == "test"
	assert event.content == "content"
	assert event.tool_name is None
	assert event.tool_args is None
	assert event.tool_call_id is None
	assert event.callback_type is None


def test_agent_event_full():
	event = AgentEvent(
		type="test",
		content="content",
		tool_name="tool",
		tool_args={"arg": 1},
		tool_call_id="id-123",
		callback_type="callback",
	)
	assert event.tool_name == "tool"
	assert event.tool_args == {"arg": 1}


def test_callback_context_defaults():
	ctx = CallbackContext()
	assert ctx.modified_input is None
	assert ctx.final_answer is None
	assert ctx.tool_input is None
	assert ctx.tool_result is None


def test_callback_context_to_dict():
	ctx = CallbackContext()
	ctx.modified_input = "mod"
	d = ctx.to_dict()
	assert d["modified_input"] == "mod"
	assert d["final_answer"] is None
