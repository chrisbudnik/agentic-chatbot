from typing import List, AsyncIterator, Dict, Any
import json
from openai import AsyncOpenAI
from app.agents.base import BaseAgent, AgentEvent
from app.tools.base import BaseTool
from app.core.config import settings


async def simple_before_callback(user_input: str, history: List[dict]):
    """
    Example before callback that appends a string to the user input.
    """
    print(f"DEBUG: Executing simple_before_callback with input: {user_input}")
    return user_input + " [Modified by Before Callback]"

async def simple_after_callback(final_answer: AgentEvent) -> List[AgentEvent]:
    """
    Example after callback that adds a thought event before the final answer.
    """
    print("DEBUG: Executing simple_after_callback")
    extra_event = AgentEvent(
        type="thought", 
        content="This thought was added by the after_agent_callback.",
    )
    return [extra_event, final_answer]


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

    async def _process_turn(self, history: List[dict], user_input: str) -> AsyncIterator[AgentEvent]:
        # 1. Prepare Messages
        # Start with system prompt
        yield AgentEvent(type="thought", content=str(history))
        messages = [{"role": "system", "content": "You are a helpful assistant. Use tools when necessary."}]
        
        messages.extend(history)
        
        messages.append({"role": "user", "content": user_input})
        
        # 2. Prepare Tools
        openai_tools = self.get_llm_tools()

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
            # We must convert the object to a dict to append to our local messages list
            # or just rely on the object if the library supports it, but simple dict is safer for custom loops
            msg_dict = {"role": "assistant"}
            if content:
                msg_dict["content"] = content
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls
            
            messages.append(msg_dict)

            if tool_calls:
                # If there are tool calls, we consider any content as a "thought"
                if content:
                    yield AgentEvent(type="thought", content=content)
                
                for tool_call in tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = self.parse_tool_args(tool_call.function.arguments)
                    
                    yield AgentEvent(
                        type="tool_call", 
                        content=f"Calling {fn_name} with {json.dumps(fn_args)}", 
                        tool_name=fn_name, 
                        tool_args=fn_args,
                        tool_call_id=tool_call.id
                    )
                    
                    result_str = await self.execute_tool(fn_name, fn_args)
                    
                    yield AgentEvent(
                        type="tool_result", 
                        content=result_str, 
                        tool_name=fn_name, 
                        tool_call_id=tool_call.id
                    )

                    messages.append(
                        self.build_tool_result_message(tool_call.id, fn_name, result_str)
                    )
                
            else:
                if content:
                    yield AgentEvent(type="answer", content=content)

                break
