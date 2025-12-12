from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import AsyncGenerator, List
import json

from app.models.chat import Conversation, Message, TraceLog, MessageRole, TraceType
from app.schemas.chat import ConversationCreate, ChatRequest
from app.agents.base import AgentEvent
from app.agents.dummy_agent import DummyAgent, DummySearchTool, DummyAgentWithError
from app.agents.llm_agent import LLMAgent
from app.core.config import settings
from app.core.database import SessionLocal
from openai import AsyncOpenAI

# Simple Registry
AGENTS = {
    "dummy": DummyAgent(tools=[DummySearchTool()]),
    "default": LLMAgent(tools=[DummySearchTool()]),
    "dummy_error": DummyAgentWithError(tools=[DummySearchTool()])
}

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(self, title: str = "New Chat") -> Conversation:
        db_conv = Conversation(title=title)
        self.db.add(db_conv)
        await self.db.commit()
        await self.db.refresh(db_conv)
        return db_conv

    async def get_conversation(self, conversation_id: str) -> Conversation:
        result = await self.db.execute(
            select(Conversation).options(selectinload(Conversation.messages).selectinload(Message.traces)).where(Conversation.id == conversation_id)
        )
        return result.scalars().first()
        
    async def get_conversations(self, limit: int = 20):
        result = await self.db.execute(
            select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def delete_conversation(self, conversation_id: str) -> bool:
        result = await self.db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = result.scalars().first()
        if conv:
            await self.db.delete(conv)
            await self.db.commit()
            return True
        return False

    async def _get_history(self, conversation_id: str) -> List[dict]:
        stmt = select(Message).options(selectinload(Message.traces)).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        history = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                history.append({"role": "user", "content": msg.content})
            elif msg.role == MessageRole.ASSISTANT:
                # Reconstruct trace steps
                traces = sorted(msg.traces, key=lambda t: t.timestamp)
                
                tool_calls_data = []
                for t in traces:
                    if t.type == "tool_call":
                        tool_calls_data.append({
                            "id": t.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": t.tool_name,
                                "arguments": json.dumps(t.tool_args) if isinstance(t.tool_args, dict) else t.tool_args
                            }
                        })
                
                if tool_calls_data:
                    # Assistant Trace Message
                    content = None
                    for t in traces:
                        if t.type == "thought":
                             content = t.content
                             break
                    
                    asst_step = {
                        "role": "assistant",
                        "tool_calls": tool_calls_data
                    }
                    if content:
                        asst_step["content"] = content
                    history.append(asst_step)
                    
                    # Tool Results
                    for t in traces:
                        if t.type == "tool_result":
                             history.append({
                                "role": "tool",
                                "tool_call_id": t.tool_call_id,
                                "name": t.tool_name,
                                "content": t.content
                            })
                    
                    # Final Answer
                    if msg.content:
                        history.append({"role": "assistant", "content": msg.content})
                else:
                    # Simple answer
                    if msg.content:
                        history.append({"role": "assistant", "content": msg.content})
                        
        return history

    async def process_message(self, conversation_id: str, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Orchestrates the message processing:
        1. Save User Message
        2. Run Agent
        3. Save Agent Traces & Response
        4. Yield Sentinel Events for proper frontend Parsing
        """
        
        # 1. Save User Message
        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=request.content
        )
        self.db.add(user_msg)
        await self.db.commit()
        
        # 2. Load Agent
        agent = AGENTS.get(request.agent_id, AGENTS["default"])
        
        # Load History
        history = await self._get_history(conversation_id)
        # Exclude the just-added user message from history if it was fetched?
        # get_history fetches all. process_turn takes history + user_input.
        # LLMAgent adds user_input to messages.
        # So history should NOT include the current user_input.
        # We just saved user_msg. So _get_history probably included it.
        # We should remove the last item if it matches the current input or just query excluding it?
        # Simpler: query all messages EXCEPT the one we just added? 
        # Or just pass the recent history and let process_turn handle it?
        # LLMAgent.process_turn:
        # messages.extend(history)
        # messages.append({"role": "user", "content": user_input})
        # So if history includes the last user message, we duplicate it.
        
        # Let's pop the last message from history if it is the user message we just added.
        if history and history[-1]["role"] == "user" and history[-1]["content"] == request.content:
             history.pop()

        # 3. Create Assistant Message Placeholder (to link traces)
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="" # Will fill later
        )
        self.db.add(assistant_msg)
        await self.db.commit()
        await self.db.refresh(assistant_msg)
        assistant_msg_id = assistant_msg.id

        final_answer_chunks = []

        # 4. Stream Agent Events
        async for event in agent.process_turn(history, request.content):
            # Save Trace
            if event.type != "answer":
                trace = TraceLog(
                    message_id=assistant_msg_id,
                    type=event.type,
                    content=event.content,
                    tool_name=event.tool_name,
                    tool_args=event.tool_args,
                    tool_call_id=event.tool_call_id
                )
                self.db.add(trace)
                await self.db.commit() # Commit each step for persistence
            
            # If answer, accumulate
            if event.type == "answer":
                final_answer_chunks.append(event.content)

            # Stream to Client (Server Sent Events format usually, but here JSON lines)
            yield json.dumps(event.model_dump()) + "\n"

        # 5. Update Assistant Message with Final Content
        await self.db.refresh(assistant_msg) 
        full_content = "".join(final_answer_chunks)
        assistant_msg.content = full_content
        await self.db.commit()


async def update_conversation_title(conversation_id: str, user_text: str):
    """
    Background task to generate a title for the conversation using an LLM.
    """
    try:
        # 1. Generate Title
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # Use a fast/cheap model for titles
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Generate a short, concise title (max 6 words) for a chat that starts with the following user message. Do not use quotes. Output ONLY the title."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=20
        )
        title = response.choices[0].message.content.strip()
        
        # 2. Update DB
        async with SessionLocal() as session:
            # Re-fetch conversation to ensure attached to this session
            result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
            conv = result.scalars().first()
            if conv:
                conv.title = title
                session.add(conv)
                await session.commit()
    except Exception as e:
        print(f"Error generating title: {e}")
