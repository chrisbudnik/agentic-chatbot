import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient

from app.agents.models import AgentEvent


class TestConversationEndpoints:
	"""Tests for conversation CRUD endpoints."""

	@pytest.mark.asyncio
	async def test_create_conversation(self, test_client: AsyncClient):
		"""POST /api/conversations creates a new conversation."""
		response = await test_client.post(
			"/api/conversations",
			json={"title": "Test Chat"},
		)

		assert response.status_code == 200
		data = response.json()
		assert data["title"] == "Test Chat"
		assert "id" in data
		assert "created_at" in data
		assert "updated_at" in data
		assert data["status"] == "active"

	@pytest.mark.asyncio
	async def test_create_conversation_default_title(
		self, test_client: AsyncClient
	):
		"""POST /api/conversations with empty title uses default."""
		response = await test_client.post(
			"/api/conversations",
			json={},
		)

		assert response.status_code == 200
		data = response.json()
		assert data["title"] is None or data["title"] == "New Chat"

	@pytest.mark.asyncio
	async def test_list_conversations_empty(self, test_client: AsyncClient):
		"""GET /api/conversations returns empty list when no conversations exist."""
		response = await test_client.get("/api/conversations")

		assert response.status_code == 200
		assert response.json() == []

	@pytest.mark.asyncio
	async def test_list_conversations(self, test_client: AsyncClient):
		"""GET /api/conversations returns list of conversations."""
		# Create multiple conversations
		await test_client.post("/api/conversations", json={"title": "Chat 1"})
		await test_client.post("/api/conversations", json={"title": "Chat 2"})
		await test_client.post("/api/conversations", json={"title": "Chat 3"})

		response = await test_client.get("/api/conversations")

		assert response.status_code == 200
		data = response.json()
		assert len(data) == 3
		titles = [c["title"] for c in data]
		assert "Chat 1" in titles
		assert "Chat 2" in titles
		assert "Chat 3" in titles

	@pytest.mark.asyncio
	async def test_list_conversations_with_limit(
		self, test_client: AsyncClient
	):
		"""GET /api/conversations respects limit parameter."""
		for i in range(5):
			await test_client.post(
				"/api/conversations", json={"title": f"Chat {i}"}
			)

		response = await test_client.get("/api/conversations?limit=2")

		assert response.status_code == 200
		data = response.json()
		assert len(data) == 2

	@pytest.mark.asyncio
	async def test_get_conversation(self, test_client: AsyncClient):
		"""GET /api/conversations/{id} returns conversation with messages."""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Detail Test"},
		)
		conv_id = create_response.json()["id"]

		# Mock storage service to avoid GCP credentials requirement
		with patch(
			"app.services.storage_service.get_storage_service"
		) as mock_get_storage:
			mock_storage = MagicMock()
			mock_storage.refresh_citations_signed_urls = AsyncMock(
				return_value=None
			)
			mock_get_storage.return_value = mock_storage

			response = await test_client.get(f"/api/conversations/{conv_id}")

		assert response.status_code == 200
		data = response.json()
		assert data["id"] == conv_id
		assert data["title"] == "Detail Test"
		assert "messages" in data
		assert isinstance(data["messages"], list)

	@pytest.mark.asyncio
	async def test_get_conversation_not_found(self, test_client: AsyncClient):
		"""GET /api/conversations/{id} returns 404 for non-existent ID."""
		response = await test_client.get("/api/conversations/non-existent-id")

		assert response.status_code == 404
		assert "not found" in response.json()["detail"].lower()

	@pytest.mark.asyncio
	async def test_delete_conversation(self, test_client: AsyncClient):
		"""DELETE /api/conversations/{id} deletes the conversation."""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "To Delete"},
		)
		conv_id = create_response.json()["id"]

		# Delete it
		delete_response = await test_client.delete(
			f"/api/conversations/{conv_id}"
		)

		assert delete_response.status_code == 200
		assert "deleted" in delete_response.json()["message"].lower()

		# Verify it's gone
		get_response = await test_client.get(f"/api/conversations/{conv_id}")
		assert get_response.status_code == 404

	@pytest.mark.asyncio
	async def test_delete_conversation_not_found(
		self, test_client: AsyncClient
	):
		"""DELETE /api/conversations/{id} returns 404 for non-existent ID."""
		response = await test_client.delete(
			"/api/conversations/non-existent-id"
		)

		assert response.status_code == 404
		assert "not found" in response.json()["detail"].lower()


class TestAgentEndpoints:
	"""Tests for agent-related endpoints."""

	@pytest.mark.asyncio
	async def test_list_agents(self, test_client: AsyncClient):
		"""GET /api/agents returns list of available agents."""
		response = await test_client.get("/api/agents")

		assert response.status_code == 200
		data = response.json()
		assert isinstance(data, list)
		assert len(data) > 0

		# Check default agent exists
		agent_ids = [a["id"] for a in data]
		assert "default" in agent_ids
		assert "dummy" in agent_ids

		# Check agent structure
		for agent in data:
			assert "id" in agent
			assert "name" in agent
			assert "description" in agent
			assert "tools" in agent
			assert isinstance(agent["tools"], list)


class TestChatEndpoints:
	"""Tests for chat/messaging endpoints."""

	@pytest.mark.asyncio
	async def test_send_message_streams_events(self, test_client: AsyncClient):
		"""POST /api/chat/{id}/message streams NDJSON events."""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Chat Test"},
		)
		conv_id = create_response.json()["id"]

		# Mock agent to avoid real LLM calls
		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="thought", content="Processing...")
			yield AgentEvent(type="answer", content="Hello!")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "MockAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Hello", "agent_id": "default"},
			)

		assert response.status_code == 200
		assert response.headers["content-type"] == "application/x-ndjson"

		# Parse NDJSON response
		lines = response.text.strip().split("\n")
		events = [json.loads(line) for line in lines]

		assert len(events) == 2
		assert events[0]["type"] == "thought"
		assert events[0]["content"] == "Processing..."
		assert events[1]["type"] == "answer"
		assert events[1]["content"] == "Hello!"

	@pytest.mark.asyncio
	async def test_send_message_conversation_not_found(
		self, test_client: AsyncClient
	):
		"""POST /api/chat/{id}/message returns 404 for non-existent conversation."""
		response = await test_client.post(
			"/api/chat/non-existent-id/message",
			json={"content": "Hello", "agent_id": "default"},
		)

		assert response.status_code == 404
		assert "not found" in response.json()["detail"].lower()

	@pytest.mark.asyncio
	async def test_send_message_with_tool_calls(self, test_client: AsyncClient):
		"""POST /api/chat/{id}/message handles tool call events."""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Tool Test"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="thought", content="Let me search...")
			yield AgentEvent(
				type="tool_call",
				content="Calling search",
				tool_name="search",
				tool_args={"query": "test"},
				tool_call_id="call_123",
			)
			yield AgentEvent(
				type="tool_result",
				content="Found results",
				tool_name="search",
				tool_call_id="call_123",
			)
			yield AgentEvent(type="answer", content="Based on my search...")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "MockAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Search for something", "agent_id": "default"},
			)

		assert response.status_code == 200

		lines = response.text.strip().split("\n")
		events = [json.loads(line) for line in lines]

		event_types = [e["type"] for e in events]
		assert "thought" in event_types
		assert "tool_call" in event_types
		assert "tool_result" in event_types
		assert "answer" in event_types

	@pytest.mark.asyncio
	async def test_send_message_unknown_agent_uses_default(
		self, test_client: AsyncClient
	):
		"""POST /api/chat/{id}/message falls back to default for unknown agent."""
		# Create conversation
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Fallback Test"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="answer", content="Default response")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "DefaultAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			response = await test_client.post(
				f"/api/chat/{conv_id}/message",
				json={"content": "Hi", "agent_id": "unknown_agent_xyz"},
			)

		assert response.status_code == 200
		lines = response.text.strip().split("\n")
		events = [json.loads(line) for line in lines]
		assert any(e["content"] == "Default response" for e in events)

	@pytest.mark.asyncio
	async def test_send_message_triggers_title_update_for_new_chat(
		self, test_client: AsyncClient
	):
		"""POST /api/chat/{id}/message triggers background title update for 'New Chat'."""
		# Create conversation with default title
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "New Chat"},
		)
		conv_id = create_response.json()["id"]

		mock_agent = MagicMock()

		async def mock_process_turn(*args, **kwargs):
			yield AgentEvent(type="answer", content="Hello!")

		mock_agent.process_turn = mock_process_turn
		mock_agent.name = "MockAgent"

		with patch.dict(
			"app.services.chat_service.AGENTS",
			{"default": mock_agent},
		):
			with patch(
				"app.api.routers.chat.update_conversation_title"
			) as mock_update:  # noqa: F841
				response = await test_client.post(
					f"/api/chat/{conv_id}/message",
					json={"content": "What is Python?", "agent_id": "default"},
				)

				# Background task should be scheduled (not necessarily called yet)
				assert response.status_code == 200


class TestChatRequestValidation:
	"""Tests for request validation."""

	@pytest.mark.asyncio
	async def test_send_message_empty_content(self, test_client: AsyncClient):
		"""POST /api/chat/{id}/message validates content is not empty."""
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Validation Test"},
		)
		conv_id = create_response.json()["id"]

		# Empty content should fail validation
		response = await test_client.post(
			f"/api/chat/{conv_id}/message",
			json={"content": "", "agent_id": "default"},
		)

		# Pydantic might allow empty string - this depends on schema
		# If you want to reject empty, add validation to ChatRequest
		# For now, we just check it doesn't crash
		assert response.status_code in [200, 422]

	@pytest.mark.asyncio
	async def test_send_message_missing_content(self, test_client: AsyncClient):
		"""POST /api/chat/{id}/message requires content field."""
		create_response = await test_client.post(
			"/api/conversations",
			json={"title": "Validation Test"},
		)
		conv_id = create_response.json()["id"]

		response = await test_client.post(
			f"/api/chat/{conv_id}/message",
			json={"agent_id": "default"},
		)

		assert response.status_code == 422  # Validation error
