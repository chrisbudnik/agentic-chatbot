from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- Conversation Schemas ---
class ConversationBase(BaseModel):
	title: Optional[str] = None


class ConversationCreate(ConversationBase):
	pass


class Conversation(ConversationBase):
	id: str
	created_at: datetime
	updated_at: datetime
	status: str

	class Config:
		from_attributes = True


# --- Trace/Step Schemas ---
class TraceLogBase(BaseModel):
	type: str
	content: Optional[str] = None
	tool_name: Optional[str] = None
	tool_args: Optional[Dict[str, Any]] = None


class TraceLog(TraceLogBase):
	id: str
	timestamp: datetime

	class Config:
		from_attributes = True


# --- Message Schemas ---
class MessageBase(BaseModel):
	role: str
	content: str


class MessageCreate(MessageBase):
	pass


class Message(MessageBase):
	id: str
	created_at: datetime
	traces: List[TraceLog] = []

	class Config:
		from_attributes = True


class ConversationDetail(Conversation):
	messages: List[Message] = []


# --- API IO ---
class ChatRequest(BaseModel):
	content: str
	agent_id: str = "default"


class FeedbackCreate(BaseModel):
	rating: int
	comment: Optional[str] = None


class AgentInfo(BaseModel):
	id: str
	name: str
	description: str
	tools: List[str]
