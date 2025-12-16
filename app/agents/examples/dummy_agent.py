from typing import AsyncIterator, List

from app.agents.base import BaseAgent
from app.agents.models import AgentEvent
from app.agents.models import CallbackContext
import asyncio


class DummyAgent(BaseAgent):
	async def _process_turn(
		self, history: List[dict], user_input: str, callback_context: CallbackContext
	) -> AsyncIterator[AgentEvent]:
		yield AgentEvent(type="thought", content="Thinking...")
		await asyncio.sleep(0.3)

		yield AgentEvent(
			type="tool_call",
			content="Searching...",
			tool_name="search_tool",
		)
		result = await self.tools["search_tool"].run(query=user_input)
		yield AgentEvent(type="tool_result", content=result)

		yield AgentEvent(
			type="answer",
			content=f"Search results for '{user_input}': {result}",
		)


class DummyAgentWithError(BaseAgent):
	async def _process_turn(
		self, history: List[dict], user_input: str
	) -> AsyncIterator[AgentEvent]:
		try:
			raise ValueError("This is ValueError message")

		except ValueError as e:
			yield AgentEvent(type="error", content=f"{type(e).__name__}: {e}")
