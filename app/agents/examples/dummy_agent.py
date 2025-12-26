from typing import AsyncIterator, List

from app.agents.base import BaseAgent
from app.agents.models import AgentEvent, CitationEvent, CitationItem
from app.agents.models import CallbackContext
import asyncio


class DummyAgent(BaseAgent):
	async def _process_turn(
		self,
		history: List[dict],
		user_input: str,
		callback_context: CallbackContext,
	) -> AsyncIterator[AgentEvent]:
		yield AgentEvent(type="thought", content="Thinking...")
		await asyncio.sleep(0.3)

		yield AgentEvent(
			type="tool_call",
			content="Searching...",
			tool_name="search_tool",
		)
		search_tool = next(
			(t for t in self.tools if t.name == "search_tool"), None
		)
		result = (
			await search_tool.run(context=callback_context, query=user_input)
			if search_tool
			else "Tool not found"
		)
		yield AgentEvent(type="tool_result", content=str(result))

		yield CitationEvent(
			content="Found some citations",
			citations=[
				CitationItem(
					source_type="website",
					title="https://example.com/1",
					url="https://example.com/1",
				),
				CitationItem(
					source_type="website",
					title="https://example.com/2",
					url="https://example.com/2",
				),
			],
		)

		yield AgentEvent(
			type="answer",
			content=f"Search results for '{user_input}': {result}",
		)


class DummyAgentWithError(BaseAgent):
	async def _process_turn(
		self,
		history: List[dict],
		user_input: str,
		callback_context: CallbackContext,
	) -> AsyncIterator[AgentEvent]:
		try:
			raise ValueError("This is ValueError message")

		except ValueError as e:
			yield AgentEvent(type="error", content=f"{type(e).__name__}: {e}")
