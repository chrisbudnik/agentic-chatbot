import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.chat import (
	Conversation,
	Message,
	MessageRole,
	TraceLog,
)
from app.services.memory_service import MemoryService
from app.agents.models import AgentEvent, CitationEvent, CitationItem


async def _create_conversation(session: AsyncSession) -> Conversation:
	conv = Conversation(title="Test")
	session.add(conv)
	await session.commit()
	await session.refresh(conv)
	return conv


@pytest.mark.asyncio
async def test_get_openai_history_simple_user_and_assistant(
	db_session: AsyncSession,
):
	conv = await _create_conversation(db_session)

	user = Message(
		conversation_id=conv.id,
		role=MessageRole.USER,
		content="Hi",
	)
	assistant = Message(
		conversation_id=conv.id,
		role=MessageRole.ASSISTANT,
		content="Hello!",
	)
	db_session.add_all([user, assistant])
	await db_session.commit()

	mem = MemoryService(db_session)
	history = await mem.get_openai_history(conv.id)

	assert history == [
		{"role": "user", "content": "Hi"},
		{"role": "assistant", "content": "Hello!"},
	]


@pytest.mark.asyncio
async def test_get_openai_history_tool_call_roundtrip(db_session: AsyncSession):
	conv = await _create_conversation(db_session)

	# user message
	user = Message(
		conversation_id=conv.id,
		role=MessageRole.USER,
		content="Search for cats",
	)

	# assistant message with traces representing tool calling + final answer
	assistant = Message(
		conversation_id=conv.id,
		role=MessageRole.ASSISTANT,
		content="Cats are great.",
	)
	db_session.add_all([user, assistant])
	await db_session.commit()
	await db_session.refresh(assistant)

	trace_thought = TraceLog(
		message_id=assistant.id,
		type="thought",
		content="Let me search that.",
	)
	trace_call = TraceLog(
		message_id=assistant.id,
		type="tool_call",
		tool_name="search",
		tool_call_id="call_1",
		tool_args={"q": "cats"},
	)
	trace_result = TraceLog(
		message_id=assistant.id,
		type="tool_result",
		tool_name="search",
		tool_call_id="call_1",
		content="Result: cats...",
	)
	db_session.add_all([trace_thought, trace_call, trace_result])
	await db_session.commit()

	mem = MemoryService(db_session)
	history = await mem.get_openai_history(conv.id)

	assert history[0] == {"role": "user", "content": "Search for cats"}

	# assistant tool call step
	assert history[1]["role"] == "assistant"
	assert history[1]["content"] == "Let me search that."
	assert history[1]["tool_calls"] == [
		{
			"id": "call_1",
			"type": "function",
			"function": {
				"name": "search",
				"arguments": json.dumps({"q": "cats"}),
			},
		}
	]

	# tool result
	assert history[2] == {
		"role": "tool",
		"tool_call_id": "call_1",
		"name": "search",
		"content": "Result: cats...",
	}

	# final assistant answer
	assert history[3] == {"role": "assistant", "content": "Cats are great."}


@pytest.mark.asyncio
async def test_exclude_message_ids_and_persistence_helpers(
	db_session: AsyncSession,
):
	conv = await _create_conversation(db_session)
	mem = MemoryService(db_session)

	# Persist a user message and ensure we can exclude it from history.
	user_msg = await mem.create_user_message(
		conversation_id=conv.id, content="Hi"
	)
	history = await mem.get_openai_history(
		conv.id, exclude_message_ids={user_msg.id}
	)
	assert history == []

	# Create assistant placeholder and persist a trace + final answer.
	assistant_msg = await mem.create_assistant_placeholder(
		conversation_id=conv.id
	)
	await mem.append_trace(
		assistant_message_id=assistant_msg.id,
		event=AgentEvent(type="thought", content="Thinking..."),
	)
	await mem.finalize_assistant_message(
		assistant_message_id=assistant_msg.id, content="Done."
	)

	# Verify the reconstructed history includes assistant final content.
	history2 = await mem.get_openai_history(conv.id)
	assert history2[-1] == {"role": "assistant", "content": "Done."}


# ============================================================
# NEW TESTS: Edge Cases and Additional Coverage
# ============================================================


@pytest.mark.asyncio
async def test_get_openai_history_empty_conversation(db_session: AsyncSession):
	"""Returns [] for new conversations with no messages."""
	conv = await _create_conversation(db_session)
	mem = MemoryService(db_session)

	history = await mem.get_openai_history(conv.id)

	assert history == []


@pytest.mark.asyncio
async def test_get_openai_history_nonexistent_conversation(
	db_session: AsyncSession,
):
	"""Returns [] for conversation IDs that don't exist."""
	mem = MemoryService(db_session)

	history = await mem.get_openai_history("nonexistent-conv-id")

	assert history == []


@pytest.mark.asyncio
async def test_multiple_tool_calls_in_single_turn(db_session: AsyncSession):
	"""Multiple tool calls in one turn are reconstructed correctly in OpenAI format."""
	conv = await _create_conversation(db_session)

	user = Message(
		conversation_id=conv.id,
		role=MessageRole.USER,
		content="Search for cats and dogs",
	)
	assistant = Message(
		conversation_id=conv.id,
		role=MessageRole.ASSISTANT,
		content="Here's what I found about cats and dogs.",
	)
	db_session.add_all([user, assistant])
	await db_session.commit()
	await db_session.refresh(assistant)

	# Two tool calls in the same turn
	traces = [
		TraceLog(
			message_id=assistant.id,
			type="thought",
			content="I'll search for both.",
		),
		TraceLog(
			message_id=assistant.id,
			type="tool_call",
			tool_name="search",
			tool_call_id="call_cats",
			tool_args={"query": "cats"},
		),
		TraceLog(
			message_id=assistant.id,
			type="tool_call",
			tool_name="search",
			tool_call_id="call_dogs",
			tool_args={"query": "dogs"},
		),
		TraceLog(
			message_id=assistant.id,
			type="tool_result",
			tool_name="search",
			tool_call_id="call_cats",
			content="Cats are felines...",
		),
		TraceLog(
			message_id=assistant.id,
			type="tool_result",
			tool_name="search",
			tool_call_id="call_dogs",
			content="Dogs are canines...",
		),
	]
	db_session.add_all(traces)
	await db_session.commit()

	mem = MemoryService(db_session)
	history = await mem.get_openai_history(conv.id)

	# Structure: user, assistant(tool_calls), tool, tool, assistant(answer)
	assert history[0]["role"] == "user"

	# Assistant message should have both tool_calls
	assert history[1]["role"] == "assistant"
	assert len(history[1]["tool_calls"]) == 2

	tool_call_ids = [tc["id"] for tc in history[1]["tool_calls"]]
	assert "call_cats" in tool_call_ids
	assert "call_dogs" in tool_call_ids

	# Two tool result messages
	tool_results = [h for h in history if h.get("role") == "tool"]
	assert len(tool_results) == 2

	# Final answer
	assert history[-1]["role"] == "assistant"
	assert history[-1]["content"] == "Here's what I found about cats and dogs."


@pytest.mark.asyncio
async def test_finalize_assistant_message_nonexistent_id(
	db_session: AsyncSession,
):
	"""finalize_assistant_message does not crash when message doesn't exist."""
	mem = MemoryService(db_session)

	# Should not raise an exception
	await mem.finalize_assistant_message(
		assistant_message_id="nonexistent-message-id",
		content="This should be ignored.",
	)

	# Verify no side effects - no messages created
	result = await db_session.execute(
		select(Message).where(Message.id == "nonexistent-message-id")
	)
	assert result.scalars().first() is None


@pytest.mark.asyncio
async def test_append_citations_trace(db_session: AsyncSession):
	"""CitationEvent creates TraceLog with linked Citation rows."""
	conv = await _create_conversation(db_session)
	mem = MemoryService(db_session)

	assistant_msg = await mem.create_assistant_placeholder(
		conversation_id=conv.id
	)

	citation_event = CitationEvent(
		content="Found relevant sources",
		citations=[
			CitationItem(
				source_type="website",
				title="Example Article",
				url="https://example.com/article",
				text="Relevant excerpt from the article...",
			),
			CitationItem(
				source_type="pdf",
				title="Research Paper",
				url=None,
				gcs_path="gs://my-bucket/papers/research.pdf",
				page_span_start=10,
				page_span_end=15,
			),
		],
	)

	await mem.append_trace(
		assistant_message_id=assistant_msg.id,
		event=citation_event,
	)

	# Verify TraceLog created
	result = await db_session.execute(
		select(TraceLog)
		.options(selectinload(TraceLog.citations))
		.where(TraceLog.message_id == assistant_msg.id)
	)
	trace = result.scalars().first()

	assert trace is not None
	assert trace.type == "citations"
	assert trace.content == "Found relevant sources"
	assert len(trace.citations) == 2

	# Verify Citation records
	website_citation = next(
		c for c in trace.citations if c.source_type == "website"
	)
	assert website_citation.title == "Example Article"
	assert website_citation.url == "https://example.com/article"
	assert website_citation.text == "Relevant excerpt from the article..."

	pdf_citation = next(c for c in trace.citations if c.source_type == "pdf")
	assert pdf_citation.title == "Research Paper"
	assert pdf_citation.gcs_path == "gs://my-bucket/papers/research.pdf"
	assert pdf_citation.page_span_start == 10
	assert pdf_citation.page_span_end == 15


@pytest.mark.asyncio
async def test_append_trace_with_all_tool_fields(db_session: AsyncSession):
	"""Tool traces preserve tool_name, tool_args, and tool_call_id."""
	conv = await _create_conversation(db_session)
	mem = MemoryService(db_session)

	assistant_msg = await mem.create_assistant_placeholder(
		conversation_id=conv.id
	)

	tool_call_event = AgentEvent(
		type="tool_call",
		content="Calling search tool",
		tool_name="advanced_search",
		tool_args={
			"query": "test query",
			"limit": 10,
			"filters": {"type": "pdf"},
		},
		tool_call_id="call_xyz789",
	)

	await mem.append_trace(
		assistant_message_id=assistant_msg.id,
		event=tool_call_event,
	)

	# Verify all fields preserved
	result = await db_session.execute(
		select(TraceLog).where(TraceLog.message_id == assistant_msg.id)
	)
	trace = result.scalars().first()

	assert trace is not None
	assert trace.type == "tool_call"
	assert trace.content == "Calling search tool"
	assert trace.tool_name == "advanced_search"
	assert trace.tool_call_id == "call_xyz789"
	assert trace.tool_args == {
		"query": "test query",
		"limit": 10,
		"filters": {"type": "pdf"},
	}


@pytest.mark.asyncio
async def test_append_trace_tool_result_with_all_fields(
	db_session: AsyncSession,
):
	"""Tool result traces preserve all relevant fields."""
	conv = await _create_conversation(db_session)
	mem = MemoryService(db_session)

	assistant_msg = await mem.create_assistant_placeholder(
		conversation_id=conv.id
	)

	tool_result_event = AgentEvent(
		type="tool_result",
		content="Found 5 documents matching your query.",
		tool_name="advanced_search",
		tool_call_id="call_xyz789",
	)

	await mem.append_trace(
		assistant_message_id=assistant_msg.id,
		event=tool_result_event,
	)

	result = await db_session.execute(
		select(TraceLog).where(TraceLog.message_id == assistant_msg.id)
	)
	trace = result.scalars().first()

	assert trace.type == "tool_result"
	assert trace.content == "Found 5 documents matching your query."
	assert trace.tool_name == "advanced_search"
	assert trace.tool_call_id == "call_xyz789"
