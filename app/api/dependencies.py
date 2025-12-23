from fastapi import Depends
from app.core.database import get_db, AsyncSession
from app.services.storage_service import StorageService, get_storage_service
from app.services.chat_service import ChatService
from typing import Annotated


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]


def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
	"""Function dependency to get ChatService instance."""
	return ChatService(db)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
