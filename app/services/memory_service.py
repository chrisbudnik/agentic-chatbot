from __future__ import annotations

import json
from typing import List, Optional, Sequence, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.models import AgentEvent
from app.models.chat import Message, MessageRole, TraceLog
from app.schemas.openai_chat import (
	OpenAIChatMessage,
	OpenAIToolCall,
	OpenAIToolFunction,
)


class MemoryService:
	"""
	Single-responsibility service for translating DB chat state into OpenAI
	`messages` and persisting agent traces / outputs back into the DB.
	"""

	def __init__(self, db: AsyncSession):
		self.db = db

	# ============================================================
	# READ: DB -> OpenAI messages
	# ============================================================

	async def get_openai_history(
		self,
		conversation_id: str,
		*,
		exclude_message_ids: Optional[Set[str]] = None,
	) -> List[dict]:
		"""
		Build OpenAI-compatible `messages` for the conversation so the agent can run.
		Optionally exclude freshly-created DB messages (e.g., the current user input).
		"""

		messages = await self._fetch_messages(conversation_id)
		if exclude_message_ids:
			messages = [m for m in messages if m.id not in exclude_message_ids]

		openai_msgs = self._messages_to_openai_history(messages)
		return [m.to_openai_dict() for m in openai_msgs]

	async def _fetch_messages(self, conversation_id: str) -> List[Message]:
		"""Fetch all messages (and traces) for a conversation in chronological order."""

		stmt = (
			select(Message)
			.options(selectinload(Message.traces))
			.where(Message.conversation_id == conversation_id)
			.order_by(Message.created_at)
		)
		result = await self.db.execute(stmt)
		return list(result.scalars().all())

	def _messages_to_openai_history(
		self, messages: Sequence[Message]
	) -> List[OpenAIChatMessage]:
		"""Convert persisted DB messages into a typed list of OpenAI chat messages."""
		history: List[OpenAIChatMessage] = []
		for msg in messages:
			if msg.role == MessageRole.USER:
				history.append(
					OpenAIChatMessage(
						role="user",
						content=msg.content,
					)
				)
				continue

			if msg.role == MessageRole.ASSISTANT:
				history.extend(self._assistant_message_to_openai(msg))
				continue

		return history

	def _assistant_message_to_openai(
		self, msg: Message
	) -> List[OpenAIChatMessage]:
		"""
		Reconstruct the assistant portion of a turn from trace logs plus the final answer.
		This produces the OpenAI sequence: assistant(tool_calls) → tool(results) → assistant(answer).

		We map:
		- trace type "tool_call"   -> assistant message with tool_calls[]
		- trace type "tool_result" -> tool role messages
		- trace type "thought"     -> optional assistant content attached to the tool_call step
		- msg.content              -> final assistant answer
		"""
		traces = sorted(msg.traces or [], key=lambda t: t.timestamp)

		tool_calls = self._build_openai_tool_calls(traces)
		out: List[OpenAIChatMessage] = []

		if tool_calls:
			thought_content = self._first_trace_content(
				traces, trace_type="thought"
			)
			assistant_step = OpenAIChatMessage(
				role="assistant",
				content=thought_content,
				tool_calls=tool_calls,
			)
			out.append(assistant_step)

			out.extend(self._build_openai_tool_result_messages(traces))

		# Final assistant answer (if present)
		if msg.content:
			out.append(OpenAIChatMessage(role="assistant", content=msg.content))

		return out

	# ============================================================
	# BUILD: OpenAI messages helpers
	# ============================================================

	def _build_openai_tool_calls(
		self, traces: Sequence[TraceLog]
	) -> Optional[List[OpenAIToolCall]]:
		"""Build the assistant `tool_calls` array from stored `tool_call` traces."""

		calls: List[OpenAIToolCall] = []
		for t in traces:
			if t.type != "tool_call":
				continue
			calls.append(
				OpenAIToolCall(
					id=t.tool_call_id,
					type="function",
					function=OpenAIToolFunction(
						name=t.tool_name,
						arguments=self._tool_args_to_arguments_json(
							t.tool_args
						),
					),
				)
			)
		return calls or None

	def _build_openai_tool_result_messages(
		self, traces: Sequence[TraceLog]
	) -> List[OpenAIChatMessage]:
		"""Build `tool` role messages from stored `tool_result` traces."""
		out: List[OpenAIChatMessage] = []
		for t in traces:
			if t.type != "tool_result":
				continue
			out.append(
				OpenAIChatMessage(
					role="tool",
					tool_call_id=t.tool_call_id,
					name=t.tool_name,
					content=t.content,
				)
			)
		return out

	def _first_trace_content(
		self, traces: Sequence[TraceLog], *, trace_type: str
	) -> Optional[str]:
		"""Return the first non-empty trace content for a given trace type, if any."""
		for t in traces:
			if t.type == trace_type and t.content:
				return t.content
		return None

	def _tool_args_to_arguments_json(self, tool_args) -> str:
		"""Normalize tool arguments into the JSON string format OpenAI expects."""
		if tool_args is None:
			return "{}"
		if isinstance(tool_args, str):
			return tool_args
		if isinstance(tool_args, dict):
			return json.dumps(tool_args)
		# fallback: keep it representable
		return json.dumps({"value": str(tool_args)})

	# ============================================================
	# WRITE: persist messages + traces
	# ============================================================

	async def create_user_message(
		self, *, conversation_id: str, content: str
	) -> Message:
		"""Persist the user's message so the turn is durable before the agent runs."""
		msg = Message(
			conversation_id=conversation_id,
			role=MessageRole.USER,
			content=content,
		)
		self.db.add(msg)
		await self.db.commit()
		await self.db.refresh(msg)
		return msg

	async def create_assistant_placeholder(
		self, *, conversation_id: str
	) -> Message:
		"""Create the assistant message row used as the parent for streaming traces."""
		msg = Message(
			conversation_id=conversation_id,
			role=MessageRole.ASSISTANT,
			content="",
		)
		self.db.add(msg)
		await self.db.commit()
		await self.db.refresh(msg)
		return msg

	async def append_trace(
		self, *, assistant_message_id: str, event: AgentEvent
	) -> None:
		"""Persist a non-answer agent event as a `TraceLog` linked to the assistant message."""
		trace = TraceLog(
			message_id=assistant_message_id,
			type=event.type,
			content=event.content,
			tool_name=event.tool_name,
			tool_args=event.tool_args,
			tool_call_id=event.tool_call_id,
		)
		self.db.add(trace)
		await self.db.commit()

	async def finalize_assistant_message(
		self, *, assistant_message_id: str, content: str
	) -> None:
		"""Write the final assistant answer content into the placeholder message row."""
		result = await self.db.execute(
			select(Message).where(Message.id == assistant_message_id)
		)
		msg = result.scalars().first()
		if not msg:
			return
		msg.content = content
		self.db.add(msg)
		await self.db.commit()
