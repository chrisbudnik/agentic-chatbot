from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Any
from pydantic import BaseModel
import asyncio
import json

from app.tools.base import BaseTool

class AgentEvent(BaseModel):
    type: str # thought, tool_call, tool_result, answer, error
    content: str
    tool_name: str = None
    tool_args: dict = None
    tool_call_id: str = None
    callback_type: str = None

class BaseAgent(ABC):
    def __init__(self, tools: List[BaseTool] = [], before_agent_callback=None, after_agent_callback=None):
        self.tools = {t.name: t for t in tools}
        self.before_agent_callback = before_agent_callback
        self.after_agent_callback = after_agent_callback

    async def process_turn(self, history: List[dict], user_input: str) -> AsyncIterator[AgentEvent]:
        """
        Process a user input and yield events (thoughts, tool calls, final answer).
        Handles before and after agent callbacks.
        """
        # 1. Before Agent Callback
        if self.before_agent_callback:
            yield AgentEvent(type="execute_callback", content="Executing before_agent_callback", callback_type="before_agent_callback")
            try:
                # Callback should return modified user_input
                # We pass both user_input and history to the callback
                modified_input = await self.before_agent_callback(user_input, history)
                
                # If callback returns a string, we treat it as modified input
                if isinstance(modified_input, str):
                    user_input = modified_input
                    yield AgentEvent(
                        type="execute_callback_result", 
                        content=f"Modified user input: {user_input}",
                        callback_type="before_agent_callback"
                    )
                else:
                    # Optional: Handle if callback returns something else or nothing
                    pass
            except Exception as e:
                yield AgentEvent(type="error", content=f"Error in before_agent_callback: {str(e)}")

        # 2. Main Agent Logic
        final_answer_event = None
        async for event in self._process_turn(history, user_input):
            if event.type == "answer" and self.after_agent_callback:
                final_answer_event = event
            else:
                yield event
        
        # 3. After Agent Callback
        if final_answer_event:
            if self.after_agent_callback:
                yield AgentEvent(type="execute_callback", content="Executing after_agent_callback", callback_type="after_agent_callback")
                try:
                    # Callback takes the final answer event and returns a list of events (or a single event)
                    result = await self.after_agent_callback(final_answer_event)
                    
                    if isinstance(result, AgentEvent):
                        yield result
                    elif isinstance(result, list):
                        for e in result:
                            if isinstance(e, AgentEvent):
                                yield e
                    else:
                        # If callback didn't return a valid event structure, just yield original
                        yield final_answer_event
                except Exception as e:
                    yield AgentEvent(type="error", content=f"Error in after_agent_callback: {str(e)}")
                    yield final_answer_event # Ensure user gets the answer even if callback fails
            else:
                yield final_answer_event

    @abstractmethod
    async def _process_turn(self, history: List[dict], user_input: str) -> AsyncIterator[AgentEvent]:
        """
        Internal method for processing the turn, to be implemented by subclasses.
        """
        pass

# --- Dummy Implementation for Testing ---

class DummySearchTool(BaseTool):
    name = "search_tool"
    description = "Searches the database for information."

    class Input(BaseModel):
        query: str
    
    input_schema = Input

    async def run(self, query: str):
        await asyncio.sleep(1) # simulate latency
        return f"Results for '{query}': Found 3 documents related to AI."

class DummyAgent(BaseAgent):
    """
    A dummy agent that pretends to think and use tools.
    """
    async def _process_turn(self, history: List[dict], user_input: str) -> AsyncIterator[AgentEvent]:
        # 1. Simulate Thinking
        yield AgentEvent(type="thought", content="I need to understand what the user is asking.")
        await asyncio.sleep(0.5)
        
        yield AgentEvent(type="thought", content="The user seems to be asking for information. I should check the search tool.")
        await asyncio.sleep(0.5)

        # 2. Simulate Tool Call
        tool_name = "search_tool"
        tool_args = {"query": user_input}
        
        yield AgentEvent(type="tool_call", content="Calling search...", tool_name=tool_name, tool_args=tool_args)
        
        # 3. Execution (In a real agent, the Controller does this, but here we do it inline for simplicity or delegate)
        if tool_name in self.tools:
            result = await self.tools[tool_name].run(**tool_args)
            yield AgentEvent(type="tool_result", content=str(result), tool_name=tool_name)
        
        await asyncio.sleep(0.5)
        
        yield AgentEvent(type="thought", content="I have the info. Now I will answer.")
        

        # 4. Final Answer
        yield AgentEvent(type="answer", content=f"Based on my search for '{user_input}', I found that there are relevant documents.")
        
        # 5. Citations
        yield AgentEvent(type="citations", content=json.dumps([
            {"title": "Understanding AI Agents", "url": "https://example.com/ai-agents"},
            {"title": "Future of LLMs", "url": "https://example.com/llm-future"}
        ]))
