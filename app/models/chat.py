from datetime import datetime, timezone
import uuid
from sqlalchemy import (
	Column,
	String,
	DateTime,
	ForeignKey,
	Text,
	Integer,
	JSON,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class MessageRole(str, enum.Enum):
	USER = "user"
	ASSISTANT = "assistant"
	SYSTEM = "system"


class TraceType(str, enum.Enum):
	THOUGHT = "thought"
	TOOL_CALL = "tool_call"
	TOOL_RESULT = "tool_result"
	ERROR = "error"


class Conversation(Base):
	__tablename__ = "conversations"

	id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
	title = Column(String, nullable=True)
	created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
	updated_at = Column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)
	status = Column(String, default="active")

	messages = relationship(
		"Message",
		back_populates="conversation",
		cascade="all, delete-orphan",
	)


class Message(Base):
	__tablename__ = "messages"

	id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
	conversation_id = Column(String, ForeignKey("conversations.id"))
	role = Column(String, nullable=False)  # user, assistant, system
	content = Column(Text, nullable=True)  # Final message content
	created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

	# Metadata for metrics
	meta_data = Column(JSON, default={})

	conversation = relationship("Conversation", back_populates="messages")
	traces = relationship(
		"TraceLog",
		back_populates="message",
		cascade="all, delete-orphan",
	)
	feedback = relationship("Feedback", back_populates="message", uselist=False)


class TraceLog(Base):
	"""
	Stores the internal steps of the agent (reasoning, tool use)
	that happened *before* producing the parent Message.
	"""

	__tablename__ = "trace_logs"

	id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
	message_id = Column(String, ForeignKey("messages.id"))
	type = Column(String, nullable=False)  # thought, tool_call, tool_result
	content = Column(Text, nullable=True)  # The thought text or tool output
	tool_name = Column(String, nullable=True)
	tool_call_id = Column(String, nullable=True)
	tool_args = Column(JSON, nullable=True)
	timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

	message = relationship("Message", back_populates="traces")
	citations = relationship(
		"Citation",
		back_populates="trace",
		cascade="all, delete-orphan",
	)


class Citation(Base):
	__tablename__ = "citations"

	id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
	trace_id = Column(String, ForeignKey("trace_logs.id"), nullable=False)
	source_type = Column(String, nullable=False)

	title = Column(String, nullable=False)
	url = Column(String, nullable=True)
	text = Column(Text, nullable=True)
	page_span_start = Column(Integer, nullable=True)
	page_span_end = Column(Integer, nullable=True)
	gcs_path = Column(String, nullable=True)
	source_metadata = Column(JSON, default={})

	created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

	trace = relationship("TraceLog", back_populates="citations")


class Feedback(Base):
	__tablename__ = "feedback"

	id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
	message_id = Column(String, ForeignKey("messages.id"))
	rating = Column(Integer)  # 1 or -1
	comment = Column(Text, nullable=True)
	created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

	message = relationship("Message", back_populates="feedback")
