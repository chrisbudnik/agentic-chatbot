import json
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest
from app.agents.models import AgentEvent
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_create_conversation(db_session: AsyncSession):
	service = ChatService(db_session)
	conv = await service.create_conversation(title="Test Chat")

	assert conv.id is not None
	assert conv.title == "Test Chat"

	# Verify persistence
	fetched = await service.get_conversation(conv.id)
	assert fetched is not None
	assert fetched.id == conv.id


@pytest.mark.asyncio
async def test_get_conversation_not_found(db_session: AsyncSession):
	service = ChatService(db_session)
	fetched = await service.get_conversation("non-existent-id")
	assert fetched is None


@pytest.mark.asyncio
async def test_get_conversations(db_session: AsyncSession):
	service = ChatService(db_session)

	# Create multiple conversations
	c1 = await service.create_conversation("Chat 1")
	c2 = await service.create_conversation("Chat 2")
	c3 = await service.create_conversation("Chat 3")

	# The default ordering is updated_at desc. creation implies update.
	# Usually newer ones are first.
	conversations = await service.get_conversations(limit=10)

	assert len(conversations) == 3
	ids = [c.id for c in conversations]
	assert c3.id in ids
	assert c2.id in ids
	assert c1.id in ids


@pytest.mark.asyncio
async def test_delete_conversation(db_session: AsyncSession):
	service = ChatService(db_session)
	conv = await service.create_conversation("To Delete")

	assert await service.delete_conversation(conv.id) is True
	assert await service.get_conversation(conv.id) is None

	# Delete non-existent
	assert await service.delete_conversation("non-existent") is False


@pytest.mark.asyncio
async def test_process_message_flow(db_session: AsyncSession):
	"""
	Verify the full process_message flow:
	1. User message created
	2. Agent invoked
	3. Traces saved
	4. Answer yielded
	5. Assistant message finalized
	"""
	service = ChatService(db_session)
	conv = await service.create_conversation("Flow Test")

	# Mock the AGENTS dictionary and the agent instance
	# We use MagicMock because AsyncMock would make process_turn return a coroutine
	# but we need it to return an async generator immediately for 'async for'
	mock_agent = MagicMock()

	# Define events the agent yields
	events = [
		AgentEvent(type="thought", content="Thinking..."),
		AgentEvent(type="answer", content="Hello world"),
	]

	async def event_generator(*args, **kwargs):
		for e in events:
			yield e

	mock_agent.process_turn.side_effect = event_generator

	with patch.dict(
		"app.services.chat_service.AGENTS", {"default": mock_agent}
	):
		request = ChatRequest(agent_id="default", content="Hello agent")

		# Collect yielded strings (json lines)
		yielded_lines = []
		async for line in service.process_message(conv.id, request):
			yielded_lines.append(line)

		# Check partial JSON outputs
		parsed_events = [json.loads(line) for line in yielded_lines]
		assert len(parsed_events) == 2
		assert parsed_events[0]["type"] == "thought"
		assert parsed_events[0]["content"] == "Thinking..."
		assert parsed_events[1]["type"] == "answer"
		assert parsed_events[1]["content"] == "Hello world"

		# Verify DB state
		mem_service = MemoryService(db_session)
		history = await mem_service.get_openai_history(conv.id)

		# Should have User message and Assistant message with content
		assert len(history) == 2
		assert history[0]["role"] == "user"
		assert history[0]["content"] == "Hello agent"

		assert history[1]["role"] == "assistant"
		assert history[1]["content"] == "Hello world"
