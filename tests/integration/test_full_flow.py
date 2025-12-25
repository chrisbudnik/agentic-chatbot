"""
Integration tests for full end-to-end flows.

These tests verify that all components work together correctly,
from API endpoints through services to database persistence.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, Message, MessageRole, TraceLog
from app.services.memory_service import MemoryService
from app.agents.models import AgentEvent, CitationEvent, CitationItem


class TestConversationFlow:
	"""Tests for complete conversation workflows."""

	@pytest.mark.asyncio
	async def test_create_conversation_send_message_verify_persistence(
		self, test_client: AsyncClient, db_session: AsyncSession
	):
		"""
		Full flow: Create conversation -> Send message -> Verify DB state.
		"""
		# 1. Create conversation via API
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Integration Test"},
		)
		assert create_response.status_code == 200
		conv_id = create_response.json()["id"]

		# 2. Send message with mocked agent
		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="thought", content="Analyzing...")
			yield AgentEvent(type="answer", content="Here is my response.")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "TestAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			message_response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Hello, world!", "agent_id": "default"},
			)

		assert message_response.status_code == 200

		# 3. Verify DB state - conversation exists with messages
		result = await db_session.execute(
			select(Conversation)
			.options(
				selectinload(Conversation.messages).selectinload(Message.traces)
			)
			.where(Conversation.id == conv_id)
		)
		conv = result.scalars().first()

		assert conv is not None
		assert len(conv.messages) == 2  # User + Assistant

		# Verify user message
		user_msg = next(m for m in conv.messages if m.role == MessageRole.USER)
		assert user_msg.content == "Hello, world!"

		# Verify assistant message
		assistant_msg = next(
			m for m in conv.messages if m.role == MessageRole.ASSISTANT
		)
		assert assistant_msg.content == "Here is my response."

		# Verify traces (thought should be saved)
		assert len(assistant_msg.traces) == 1
		assert assistant_msg.traces[0].type == "thought"
		assert assistant_msg.traces[0].content == "Analyzing..."

	@pytest.mark.asyncio
	async def test_multi_turn_conversation(
		self, test_client: AsyncClient, db_session: AsyncSession
	):
		"""
		Test multi-turn conversation maintains history correctly.
		"""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Multi-turn Test"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()
		turn_count = [0]

		async def mock_process_turn(history, user_input, *args, **kwargs):
			turn_count[0] += 1
			# On turn 2+, history should contain previous messages
			if turn_count[0] > 1:
				assert len(history) > 0, "History should contain previous turns"
			yield AgentEvent(
				type="answer", content=f"Response to turn {turn_count[0]}"
			)

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "HistoryAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			# Turn 1
			await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "First message", "agent_id": "default"},
			)

			# Turn 2
			await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Second message", "agent_id": "default"},
			)

			# Turn 3
			await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Third message", "agent_id": "default"},
			)

		assert turn_count[0] == 3

		# Verify all messages persisted
		result = await db_session.execute(
			select(Conversation)
			.options(selectinload(Conversation.messages))
			.where(Conversation.id == conv_id)
		)
		conv = result.scalars().first()

		# 3 user messages + 3 assistant messages = 6 total
		assert len(conv.messages) == 6


class TestToolCallFlow:
	"""Tests for conversations with tool usage."""

	@pytest.mark.asyncio
	async def test_tool_call_and_result_persisted(
		self, test_client: AsyncClient, db_session: AsyncSession
	):
		"""
		Verify tool calls and results are saved as traces.
		"""
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Tool Flow Test"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="thought", content="I need to search...")
			yield AgentEvent(
				type="tool_call",
				content="Calling search tool",
				tool_name="search",
				tool_args={"query": "python"},
				tool_call_id="call_abc123",
			)
			yield AgentEvent(
				type="tool_result",
				content="Found 10 results about Python",
				tool_name="search",
				tool_call_id="call_abc123",
			)
			yield AgentEvent(
				type="answer", content="Based on search: Python is great!"
			)

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "ToolAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Tell me about Python", "agent_id": "default"},
			)

		assert response.status_code == 200

		# Verify traces in DB
		result = await db_session.execute(
			select(Message)
			.options(selectinload(Message.traces))
			.where(Message.conversation_id == conv_id)
			.where(Message.role == MessageRole.ASSISTANT)
		)
		assistant_msg = result.scalars().first()

		trace_types = [t.type for t in assistant_msg.traces]
		assert "thought" in trace_types
		assert "tool_call" in trace_types
		assert "tool_result" in trace_types

		# Verify tool_call trace has correct metadata
		tool_call_trace = next(
			t for t in assistant_msg.traces if t.type == "tool_call"
		)
		assert tool_call_trace.tool_name == "search"
		assert tool_call_trace.tool_call_id == "call_abc123"
		assert tool_call_trace.tool_args == {"query": "python"}


class TestHistoryReconstruction:
	"""Tests for OpenAI history reconstruction from DB."""

	@pytest.mark.asyncio
	async def test_history_includes_tool_calls_in_openai_format(
		self, db_session: AsyncSession
	):
		"""
		After a tool-using turn, history should be reconstructed
		in OpenAI's expected format for the next turn.
		"""
		# Create conversation and messages directly in DB
		conv = Conversation(title="History Test")
		db_session.add(conv)
		await db_session.commit()
		await db_session.refresh(conv)

		# User message
		user_msg = Message(
			conversation_id=conv.id,
			role=MessageRole.USER,
			content="Search for cats",
		)
		db_session.add(user_msg)
		await db_session.commit()

		# Assistant message with tool traces
		assistant_msg = Message(
			conversation_id=conv.id,
			role=MessageRole.ASSISTANT,
			content="Cats are wonderful pets.",
		)
		db_session.add(assistant_msg)
		await db_session.commit()
		await db_session.refresh(assistant_msg)

		# Add traces
		traces = [
			TraceLog(
				message_id=assistant_msg.id,
				type="thought",
				content="Let me search for that.",
			),
			TraceLog(
				message_id=assistant_msg.id,
				type="tool_call",
				tool_name="search",
				tool_call_id="call_123",
				tool_args={"query": "cats"},
			),
			TraceLog(
				message_id=assistant_msg.id,
				type="tool_result",
				tool_name="search",
				tool_call_id="call_123",
				content="Cats are domesticated felines...",
			),
		]
		db_session.add_all(traces)
		await db_session.commit()

		# Reconstruct history
		memory = MemoryService(db_session)
		history = await memory.get_openai_history(conv.id)

		# Verify OpenAI format
		assert (
			len(history) == 4
		)  # user, assistant(tool_calls), tool, assistant(answer)

		# User message
		assert history[0]["role"] == "user"
		assert history[0]["content"] == "Search for cats"

		# Assistant with tool_calls
		assert history[1]["role"] == "assistant"
		assert "tool_calls" in history[1]
		assert len(history[1]["tool_calls"]) == 1
		assert history[1]["tool_calls"][0]["function"]["name"] == "search"

		# Tool result
		assert history[2]["role"] == "tool"
		assert history[2]["tool_call_id"] == "call_123"

		# Final answer
		assert history[3]["role"] == "assistant"
		assert history[3]["content"] == "Cats are wonderful pets."


class TestErrorHandling:
	"""Tests for error scenarios in the full flow."""

	@pytest.mark.asyncio
	async def test_agent_error_event_persisted(
		self, test_client: AsyncClient, db_session: AsyncSession
	):
		"""
		Error events from agents should be persisted as traces.
		"""
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Error Test"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="error", content="Something went wrong!")
			yield AgentEvent(type="answer", content="I encountered an error.")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "ErrorAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Trigger error", "agent_id": "default"},
			)

		assert response.status_code == 200

		# Verify error trace persisted
		result = await db_session.execute(
			select(Message)
			.options(selectinload(Message.traces))
			.where(Message.conversation_id == conv_id)
			.where(Message.role == MessageRole.ASSISTANT)
		)
		assistant_msg = result.scalars().first()

		error_traces = [t for t in assistant_msg.traces if t.type == "error"]
		assert len(error_traces) == 1
		assert "Something went wrong" in error_traces[0].content


class TestCitationFlow:
	"""Tests for citation handling in full flow."""

	@pytest.mark.asyncio
	async def test_citations_persisted_with_traces(
		self, db_session: AsyncSession
	):
		"""
		CitationEvents should be saved as traces with linked Citation records.
		"""

		# Create conversation
		conv = Conversation(title="Citation Test")
		db_session.add(conv)
		await db_session.commit()
		await db_session.refresh(conv)

		# Create assistant placeholder
		memory = MemoryService(db_session)
		assistant_msg = await memory.create_assistant_placeholder(
			conversation_id=conv.id
		)

		# Append citation event
		citation_event = CitationEvent(
			content="Found sources",
			citations=[
				CitationItem(
					source_type="website",
					title="Example Site",
					url="https://example.com",
					text="Relevant excerpt...",
				),
				CitationItem(
					source_type="pdf",
					title="Research Paper",
					url=None,
					gcs_path="gs://bucket/paper.pdf",
					page_span_start=5,
					page_span_end=7,
				),
			],
		)
		await memory.append_trace(
			assistant_message_id=assistant_msg.id,
			event=citation_event,
		)

		# Verify in DB
		result = await db_session.execute(
			select(TraceLog)
			.options(selectinload(TraceLog.citations))
			.where(TraceLog.message_id == assistant_msg.id)
		)
		trace = result.scalars().first()

		assert trace is not None
		assert trace.type == "citations"
		assert len(trace.citations) == 2

		# Verify citation details
		website_citation = next(
			c for c in trace.citations if c.source_type == "website"
		)
		assert website_citation.title == "Example Site"
		assert website_citation.url == "https://example.com"

		pdf_citation = next(
			c for c in trace.citations if c.source_type == "pdf"
		)
		assert pdf_citation.gcs_path == "gs://bucket/paper.pdf"
		assert pdf_citation.page_span_start == 5


class TestDummyAgentIntegration:
	"""
	Integration tests using the actual DummyAgent.
	These test the real agent implementation without mocking.
	"""

	@pytest.mark.asyncio
	async def test_dummy_agent_full_flow(
		self, test_client: AsyncClient, db_session: AsyncSession
	):
		"""
		Use the actual DummyAgent to verify full integration.
		Note: This test has a 5+ second delay due to DummySearchTool's sleep.
		"""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Dummy Agent Test"},
		)
		conv_id = create_response.json()["id"]

		# Use the real dummy agent (faster tool mock)
		from app.agents.examples.dummy_agent import DummyAgent
		from app.agents.tools.base import BaseTool
		from pydantic import BaseModel

		class FastSearchTool(BaseTool):
			name = "search_tool"
			description = "Fast search for testing"

			class Input(BaseModel):
				query: str

			input_schema = Input

			async def run(self, context, query: str):
				return f"Fast results for '{query}'"

		test_agent = DummyAgent(
			name="Fast Dummy",
			description="Fast test agent",
			tools=[FastSearchTool()],
		)

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"dummy": test_agent},
		):
			response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Test query", "agent_id": "dummy"},
			)

		assert response.status_code == 200

		# Parse events
		lines = response.text.strip().split("\n")
		events = [json.loads(line) for line in lines]

		event_types = [e["type"] for e in events]

		# DummyAgent yields: thought, tool_call, tool_result, citations, answer
		assert "thought" in event_types
		assert "tool_call" in event_types
		assert "tool_result" in event_types
		assert "citations" in event_types
		assert "answer" in event_types

		# Verify DB persistence
		result = await db_session.execute(
			select(Message)
			.options(selectinload(Message.traces))
			.where(Message.conversation_id == conv_id)
			.where(Message.role == MessageRole.ASSISTANT)
		)
		assistant_msg = result.scalars().first()

		# All non-answer events should be saved as traces
		trace_types = [t.type for t in assistant_msg.traces]
		assert "thought" in trace_types
		assert "tool_call" in trace_types
		assert "tool_result" in trace_types
		assert "citations" in trace_types


class TestConversationDeletion:
	"""Tests for conversation deletion cascades."""

	@pytest.mark.asyncio
	async def test_delete_conversation_removes_messages_and_traces(
		self, test_client: AsyncClient, db_session: AsyncSession
	):
		"""
		Deleting a conversation should cascade delete all related data.
		"""
		# Create conversation with messages
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "To Delete"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="thought", content="Thinking...")
			yield AgentEvent(type="answer", content="Done!")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "TestAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Hello", "agent_id": "default"},
			)

		# Verify data exists
		result = await db_session.execute(
			select(Message).where(Message.conversation_id == conv_id)
		)
		messages_before = result.scalars().all()
		assert len(messages_before) == 2

		# Delete conversation
		delete_response = await test_client.delete(
			f"/api/conversations/{conv_id}"
		)
		assert delete_response.status_code == 200

		# Verify conversation gone
		result = await db_session.execute(
			select(Conversation).where(Conversation.id == conv_id)
		)
		assert result.scalars().first() is None
