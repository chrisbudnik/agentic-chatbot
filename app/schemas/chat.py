import json
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import SettingsConfigDict
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

	model_config = SettingsConfigDict(from_attributes=True)


# --- Trace/Step Schemas ---
class Citation(BaseModel):
	id: str
	trace_id: str
	source_type: str
	title: Optional[str] = None
	url: Optional[str] = None
	text: Optional[str] = None
	page_span_start: Optional[int] = None
	page_span_end: Optional[int] = None
	gcs_path: Optional[str] = None
	source_metadata: Dict[str, Any] = Field(default_factory=dict)
	created_at: datetime

	model_config = SettingsConfigDict(from_attributes=True)

	@field_validator("source_metadata", mode="before")
	@classmethod
	def _coerce_source_metadata(cls, v: Any) -> Dict[str, Any]:
		"""
		Accept legacy DB values (None / JSON 'null') and coerce them into a dict.
		Rows can have JSON null (deserialized as None). Normalize to {} for stability.
		"""
		if v is None:
			return {}

		if isinstance(v, str):
			s = v.strip()
			if s == "" or s.lower() == "null":
				return {}
			try:
				decoded = json.loads(s)
				if decoded is None:
					return {}
				if isinstance(decoded, dict):
					return decoded
			except Exception:
				# Fall through and let Pydantic raise if it's not a dict-like value.
				pass

		return v


class TraceLogBase(BaseModel):
	type: str
	content: Optional[str] = None
	tool_name: Optional[str] = None
	tool_args: Optional[Dict[str, Any]] = None
	citations: List[Citation] = Field(default_factory=list)


class TraceLog(TraceLogBase):
	id: str
	timestamp: datetime

	model_config = SettingsConfigDict(from_attributes=True)


# --- Message Schemas ---
class MessageBase(BaseModel):
	role: str
	content: str


class MessageCreate(MessageBase):
	pass


class Message(MessageBase):
	id: str
	created_at: datetime
	traces: List[TraceLog] = Field(default_factory=list)

	model_config = SettingsConfigDict(from_attributes=True)


class ConversationDetail(Conversation):
	messages: List[Message] = Field(default_factory=list)


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
