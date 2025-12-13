from pyexpat.errors import messages
from typing import List, AsyncIterator, Dict, Any
import json
from openai import AsyncOpenAI
from app.agents.base import BaseAgent, AgentEvent
from app.agents.tools.base import BaseTool
from app.core.config import settings
from app.agents.models import CallbackContext


class LLMAgent(BaseAgent):
    def __init__(
        self,
        tools: List[BaseTool] = [],
        model: str = "gpt-4.1",
        before_agent_callback=None,
        after_agent_callback=None
    ):
        super().__init__(
            tools=tools,
            name="LLM Agent",
            description="A smart agent that uses an LLM to reason and use tools.",
            model=model,
            before_agent_callback=before_agent_callback,
            after_agent_callback=after_agent_callback
        )
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def _process_turn(
            self, 
            history: List[dict], 
            user_input: str, 
            callback_context: CallbackContext
        ) -> AsyncIterator[AgentEvent]:

        # 1. Prepare Messages
        # Start with system prompt
        yield AgentEvent(type="thought", content=str(history))
        messages = [{"role": "system", "content": "You are a helpful assistant. Use tools when necessary."}]
        
        messages.extend(history)
        
        messages.append({"role": "user", "content": user_input})
        
        # 2. Prepare Tools
        openai_tools = [t.to_openai_tool() for t in self.tools.values()] if self.tools else None

        # 3. ReAct / Tool-Use Loop
        # we loop until the model decides to stop calling tools (i.e. yields an answer)
        while True:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                )
            except Exception as e:
                print(f"Error in process_turn: {str(e)}")
                yield AgentEvent(type="error", content=str(e))
                break   
            
            message = response.choices[0].message
            content = message.content
            tool_calls = message.tool_calls
            
            # Append the assistant's response to messages (context for next turn)
            msg_dict = {"role": "assistant"}
            if content:
                msg_dict["content"] = content
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls
            
            messages.append(msg_dict)

            if tool_calls:
                # If there are tool calls, we consider any content as a "thought"
                # but this occurs very infrequently since llm models are tuned to provide only params.
                if content:
                    yield AgentEvent(type="thought", content=content)
                
                for tool_call in tool_calls:

                    # new context for each tool - avoid race conditions
                    tool_context: CallbackContext = CallbackContext()
                    tool = self.tools.get(tool_call.function.name)
                    
                    if tool:
                        async for event in tool.execute(tool_call, tool_context):
                            yield event
                        tool_result = tool_context.tool_result
                    else:
                        # this error practically never happens for newer models
                        tool_result = f"Error: Tool '{tool_call.function.name}' not found." 

                    messages.append(
                        BaseTool.build_tool_result_message(
                            tool_call.id,
                            tool_call.function.name,
                            tool_result or "Error: Tool failed without returning a result."
                        )
                    )
                
            else:
                if content:
                    yield AgentEvent(type="answer", content=content)

                break
