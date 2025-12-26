from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from typing import List

from app.core.database import get_db
from app.services.chat_service import (
	ChatService,
	update_conversation_title,
	AGENTS,
)
from app.schemas.chat import (
	Conversation,
	ConversationCreate,
	ConversationDetail,
	ChatRequest,
	AgentInfo,
)
from app.core.logging import get_logger
from app.api.dependencies import StorageServiceDep, ChatServiceDep


router = APIRouter()
logger = get_logger(__name__)


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
	conv_in: ConversationCreate, db: AsyncSession = Depends(get_db)
) -> Conversation:
	service = ChatService(db)
	return await service.create_conversation(title=conv_in.title)


@router.get("/conversations", response_model=List[Conversation])
async def list_conversations(
	limit: int = 20, db: AsyncSession = Depends(get_db)
) -> List[Conversation]:
	service = ChatService(db)
	return await service.get_conversations(limit=limit)


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents() -> List[AgentInfo]:
	agents_list = []
	for agent_id, agent in AGENTS.items():
		agents_list.append(
			AgentInfo(
				id=agent_id,
				name=agent.name,
				description=agent.description,
				tools=[t.name for t in agent.tools] if agent.tools else [],
			)
		)
	return agents_list


@router.get(
	"/conversations/{conversation_id}",
	response_model=ConversationDetail,
)
async def get_conversation(
	conversation_id: str,
	chat: ChatServiceDep,
	storage: StorageServiceDep,
) -> ConversationDetail:
	logger.info(f"Fetching conversation {conversation_id} with signed URLs")
	conv = await chat.get_conversation(conversation_id)
	if not conv:
		raise HTTPException(status_code=404, detail="Conversation not found")

	# Refresh signed URLs for citations
	await storage.refresh_citations_signed_urls(conv.messages)
	return conv


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
	conversation_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
	service = ChatService(db)
	success = await service.delete_conversation(conversation_id)
	if not success:
		raise HTTPException(status_code=404, detail="Conversation not found")
	return {"message": "Conversation deleted"}


@router.post("/chat/{conversation_id}/message")
async def send_message(
	conversation_id: str,
	request: ChatRequest,
	background_tasks: BackgroundTasks,
	db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
	service = ChatService(db)
	conv = await service.get_conversation(conversation_id)
	if not conv:
		raise HTTPException(status_code=404, detail="Conversation not found")

	if conv.title == "New Chat":
		background_tasks.add_task(
			update_conversation_title,
			conversation_id,
			request.content,
		)

	return StreamingResponse(
		service.process_message(conversation_id, request),
		media_type="application/x-ndjson",
	)
