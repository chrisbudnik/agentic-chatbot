from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import AsyncGenerator
import json

from app.models.chat import (
	Conversation,
	Message,
)
from app.schemas.chat import ChatRequest
from app.agents.registry import AGENTS
from app.core.config import settings
from app.core.database import SessionLocal
from openai import AsyncOpenAI
from app.services.memory_service import MemoryService


class ChatService:
	def __init__(self, db: AsyncSession):
		self.db = db
		self.memory = MemoryService(db)

	async def create_conversation(
		self, title: str = "New Chat"
	) -> Conversation:
		db_conv = Conversation(title=title)
		self.db.add(db_conv)
		await self.db.commit()
		await self.db.refresh(db_conv)
		return db_conv

	async def get_conversation(self, conversation_id: str) -> Conversation:
		result = await self.db.execute(
			select(Conversation)
			.options(
				selectinload(Conversation.messages).selectinload(Message.traces)
			)
			.where(Conversation.id == conversation_id)
		)
		return result.scalars().first()

	async def get_conversations(self, limit: int = 20):
		result = await self.db.execute(
			select(Conversation)
			.order_by(Conversation.updated_at.desc())
			.limit(limit)
		)
		return result.scalars().all()

	async def delete_conversation(self, conversation_id: str) -> bool:
		result = await self.db.execute(
			select(Conversation).where(Conversation.id == conversation_id)
		)
		conv = result.scalars().first()
		if conv:
			await self.db.delete(conv)
			await self.db.commit()
			return True
		return False

	async def process_message(
		self, conversation_id: str, request: ChatRequest
	) -> AsyncGenerator[str, None]:
		"""
		Orchestrates the message processing:
		1. Save User Message
		2. Run Agent
		3. Save Agent Traces & Response
		4. Yield Sentinel Events for proper frontend Parsing
		"""

		# 1. Save User Message
		user_msg = await self.memory.create_user_message(
			conversation_id=conversation_id, content=request.content
		)

		# 2. Load Agent
		agent = AGENTS.get(request.agent_id, AGENTS["default"])

		# Load History (exclude the message we just created)
		history = await self.memory.get_openai_history(
			conversation_id, exclude_message_ids={user_msg.id}
		)

		# 3. Create Assistant Message Placeholder (to link traces)
		assistant_msg = await self.memory.create_assistant_placeholder(
			conversation_id=conversation_id
		)
		assistant_msg_id = assistant_msg.id

		final_answer_chunks = []

		# 4. Stream Agent Events
		async for event in agent.process_turn(history, request.content):
			if event.type != "answer":
				await self.memory.append_trace(
					assistant_message_id=assistant_msg_id, event=event
				)

			if event.type == "answer":
				final_answer_chunks.append(event.content)

			yield json.dumps(event.model_dump()) + "\n"

		# 5. Update Assistant Message with Final Content
		full_content = "".join(final_answer_chunks)
		await self.memory.finalize_assistant_message(
			assistant_message_id=assistant_msg_id, content=full_content
		)


async def update_conversation_title(conversation_id: str, user_text: str):
	"""
	Background task to generate a title for the conversation using an LLM.
	"""
	try:
		# 1. Generate Title
		client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
		response = await client.chat.completions.create(
			model="gpt-4o-mini",
			messages=[
				{
					"role": "system",
					"content": "You are a helpful assistant. Generate a short, concise title (max 6 words) for a chat that starts with the following user message. Do not use quotes. Output ONLY the title.",
				},
				{"role": "user", "content": user_text},
			],
			max_tokens=20,
		)
		title = response.choices[0].message.content.strip()

		# 2. Update DB
		async with SessionLocal() as session:
			# Re-fetch conversation to ensure attached to this session
			result = await session.execute(
				select(Conversation).where(Conversation.id == conversation_id)
			)
			conv = result.scalars().first()
			if conv:
				conv.title = title
				session.add(conv)
				await session.commit()
	except Exception as e:
		print(f"Error generating title: {e}")
