import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import (
	Conversation,
	Message,
	MessageRole,
	TraceLog,
	Citation,
)
from app.schemas.chat import ConversationDetail


@pytest.mark.asyncio
async def test_conversation_detail_serializes_with_null_citation_source_metadata(
	db_session: AsyncSession,
):
	"""
	Regression: older DB rows can store JSON `null` for citations.source_metadata.
	FastAPI/Pydantic serialization should not fail when loading a conversation.
	"""
	conv = Conversation(title="Has citations")
	db_session.add(conv)
	await db_session.commit()
	await db_session.refresh(conv)

	assistant = Message(
		conversation_id=conv.id,
		role=MessageRole.ASSISTANT,
		content="Answer with sources",
	)
	db_session.add(assistant)
	await db_session.commit()
	await db_session.refresh(assistant)

	trace = TraceLog(
		message_id=assistant.id,
		type="citations",
		content="Citations generated.",
	)
	db_session.add(trace)
	await db_session.commit()
	await db_session.refresh(trace)

	citation = Citation(
		trace_id=trace.id,
		source_type="website",
		title="Example",
		url="https://example.com",
		source_metadata=None,  # critical: should serialize as {}
	)
	db_session.add(citation)
	await db_session.commit()

	# Reload with relationships like ChatService.get_conversation()
	result = await db_session.execute(
		select(Conversation)
		.options(
			selectinload(Conversation.messages)
			.selectinload(Message.traces)
			.selectinload(TraceLog.citations)
		)
		.where(Conversation.id == conv.id)
	)
	conv_loaded = result.scalars().first()

	serialized = ConversationDetail.model_validate(
		conv_loaded, from_attributes=True
	)
	assert serialized.messages
	assert serialized.messages[0].traces
	assert serialized.messages[0].traces[0].citations
	assert serialized.messages[0].traces[0].citations[0].source_metadata == {}
