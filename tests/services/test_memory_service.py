import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.chat import Conversation, Message, MessageRole, TraceLog
from app.services.memory_service import MemoryService
from app.agents.models import AgentEvent


@pytest.fixture
async def db_session() -> AsyncSession:
	"""
	Create an isolated in-memory SQLite DB per test, including all tables.
	"""
	engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)

	SessionLocal = sessionmaker(
		autocommit=False,
		autoflush=False,
		bind=engine,
		class_=AsyncSession,
		expire_on_commit=False,
	)
	async with SessionLocal() as session:
		yield session

	await engine.dispose()


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
