from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Optional

from app.agents.tools.base import BaseTool
from app.agents.models import AgentEvent, CallbackContext
from app.agents.callbacks import run_callback_with_events
from app.agents.callbacks import (
	BeforeAgentCallback,
	AfterAgentCallback,
)


# ============================================================
# BASE AGENT
# ============================================================


class BaseAgent(ABC):
	def __init__(
		self,
		name: str = "Agent",
		description: str = "",
		system_prompt: str = "You are a helpful assistant.",
		model: str = "gpt-4.1",
		tools: Optional[List[BaseTool]] = None,
		before_agent_callback: Optional[BeforeAgentCallback] = None,
		after_agent_callback: Optional[AfterAgentCallback] = None,
	) -> None:
		self.tools = {t.name: t for t in tools} if tools else {}
		self.name = name
		self.description = description
		self.system_prompt = system_prompt
		self.model = model

		self.before_agent_callback = before_agent_callback
		self.after_agent_callback = after_agent_callback

	# ============================================================
	# BEFORE CALLBACK
	# ============================================================

	async def process_before_agent_callback(
		self,
		user_input: str,
		history: List[dict],
		context: CallbackContext,
	) -> AsyncIterator[AgentEvent]:
		if not self.before_agent_callback:
			context.modified_input = user_input
			return

		async for event in run_callback_with_events(
			callback_fn=self.before_agent_callback,
			callback_input={
				"user_input": user_input,
				"history": history,
			},
			context=context,
			context_attr="modified_input",
			callback_type="before_agent_callback",
		):
			yield event

		# If callback produced no new user input, fallback
		if context.modified_input is None:
			context.modified_input = user_input

	# ============================================================
	# AFTER CALLBACK
	# ============================================================

	async def process_after_agent_callback(
		self, final_answer: AgentEvent, context: CallbackContext
	) -> AsyncIterator[AgentEvent]:
		if not self.after_agent_callback:
			yield final_answer
			return

		async for event in run_callback_with_events(
			callback_fn=self.after_agent_callback,
			callback_input={"final_answer": final_answer},
			context=context,
			context_attr="final_answer",
			callback_type="after_agent_callback",
		):
			yield event

	# ============================================================
	# MAIN TURN PROCESSOR
	# ============================================================

	async def process_turn(
		self, history: List[dict], user_input: str
	) -> AsyncIterator[AgentEvent]:
		context = CallbackContext()

		# BEFORE CALLBACK
		async for event in self.process_before_agent_callback(
			user_input, history, context
		):
			yield event

		# MAIN AGENT LOGIC
		final_answer_event = None
		user_input = context.modified_input or user_input

		async for event in self._process_turn(
			history=history,
			user_input=user_input,
			callback_context=context,
		):
			if event.type == "answer":
				final_answer_event = event
				break
			yield event

		# AFTER CALLBACK
		if final_answer_event:
			async for event in self.process_after_agent_callback(
				final_answer_event, context
			):
				yield event

	# ============================================================
	# ABSTRACT MAIN STEP
	# ============================================================

	@abstractmethod
	async def _process_turn(
		self,
		history: List[dict],
		user_input: str,
		callback_context: CallbackContext,
		*args,
		**kwargs,
	) -> AsyncIterator[AgentEvent]:
		"""
		Abstract method to process a turn. Implemented by subclasses.
		"""
		pass
