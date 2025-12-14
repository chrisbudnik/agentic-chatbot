import pytest
from typing import List, AsyncIterator
from app.agents.base import BaseAgent, AgentEvent, CallbackContext


class MockAgent(BaseAgent):
	"""Concrete implementation of BaseAgent for testing."""

	async def _process_turn(
		self,
		history: List[dict],
		user_input: str,
		callback_context: CallbackContext,
		*args,
		**kwargs,
	) -> AsyncIterator[AgentEvent]:
		yield AgentEvent(type="thought", content="Processing...")
		yield AgentEvent(type="answer", content=f"Echo: {user_input}")


@pytest.mark.asyncio
async def test_base_agent_process_turn():
	agent = MockAgent(name="TestAgent")
	events = []
	async for event in agent.process_turn([], "Hello"):
		assert isinstance(event, AgentEvent)
		events.append(event)

	# Expected: thought("Processing..."), answer("Echo: Hello")
	assert len(events) == 2
	assert events[0].type == "thought"
	assert events[1].type == "answer"
	assert events[1].content == "Echo: Hello"


@pytest.mark.asyncio
async def test_before_callback_modifies_input():
	async def before_cb(user_input, history, context):
		yield AgentEvent(type="execute_callback", content="Before")
		context.modified_input = f"Modified {user_input}"

	agent = MockAgent(name="TestAgent", before_agent_callback=before_cb)

	events = []
	async for event in agent.process_turn([], "Hello"):
		events.append(event)

	# Events structure:
	# 0. execute_callback (Start)
	# 1. execute_callback (Yielded by cb)
	# 2. execute_callback_result (End)
	# 3. thought
	# 4. answer

	assert len(events) == 5
	assert events[1].type == "execute_callback"
	assert events[1].content == "Before"

	answer_event = events[-1]
	assert answer_event.type == "answer"
	assert answer_event.content == "Echo: Modified Hello"


@pytest.mark.asyncio
async def test_after_callback_modifies_output():
	async def after_cb(final_answer, context):
		yield AgentEvent(type="execute_callback", content="After")
		yield AgentEvent(
			type="answer", content=f"{final_answer.content} Verified"
		)

	agent = MockAgent(name="TestAgent", after_agent_callback=after_cb)

	events = []
	async for event in agent.process_turn([], "Hello"):
		events.append(event)

	# Events structure:
	# 0. thought
	# 1. execute_callback (Start)
	# 2. execute_callback (Yielded by cb)
	# 3. answer (Yielded by cb)
	# 4. execute_callback_result (End)

	assert len(events) == 5
	assert events[0].type == "thought"
	assert events[2].content == "After"

	ans_events = [e for e in events if e.type == "answer"]
	assert len(ans_events) == 1
	assert "Verified" in ans_events[0].content


@pytest.mark.asyncio
async def test_callbacks_chain_context():
	"""Test that context is preserved/passed correctly."""

	async def before_cb(user_input, history, context):
		# We need to set the context attribute to return a value in the new system
		# (Assuming run_callback_with_events logic for non-generator return works)
		# Actually the test originally returned a string.
		# Returning a string -> Case 2 in run_callback_with_events -> sets context variable.
		return f"{user_input} [Checked]"

	async def after_cb(final_answer, context):
		# Returning an event -> Case 3 -> yields event.
		return AgentEvent(
			type="answer", content=f"{final_answer.content} [Finalized]"
		)

	agent = MockAgent(
		name="TestAgent",
		before_agent_callback=before_cb,
		after_agent_callback=after_cb,
	)

	events = []
	async for event in agent.process_turn([], "Input"):
		events.append(event)

	# Check that we got the final modified answer
	ans_events = [e for e in events if e.type == "answer"]
	assert len(ans_events) == 1
	final_event = ans_events[0]

	# Input -> "Input [Checked]" (modified by before_cb return value)
	# Agent -> "Echo: Input [Checked]"
	# After -> "Echo: Input [Checked] [Finalized]" (returned by after_cb)

	assert "Input [Checked] [Finalized]" in final_event.content
