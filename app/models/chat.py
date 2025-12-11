from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active")

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String, nullable=False) # user, assistant, system
    content = Column(Text, nullable=True) # Final message content
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for metrics
    meta_data = Column(JSON, default={})

    conversation = relationship("Conversation", back_populates="messages")
    traces = relationship("TraceLog", back_populates="message", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="message", uselist=False)

class TraceLog(Base):
    """
    Stores the internal steps of the agent (reasoning, tool use) 
    that happened *before* producing the parent Message.
    """
    __tablename__ = "trace_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("messages.id"))
    type = Column(String, nullable=False) # thought, tool_call, tool_result
    content = Column(Text, nullable=True) # The thought text or tool output
    tool_name = Column(String, nullable=True)
    tool_call_id = Column(String, nullable=True)
    tool_args = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="traces")

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("messages.id"))
    rating = Column(Integer) # 1 or -1
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")
