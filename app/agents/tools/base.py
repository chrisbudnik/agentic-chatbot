from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Type, Dict, Optional, Callable, AsyncIterator, Union
import json

from app.agents.models import AgentEvent, CallbackContext
from app.agents.callbacks import run_callback_with_events
from app.agents.callbacks import BeforeToolCallback, AfterToolCallback
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall


# ============================================================
# BASE TOOL
# ============================================================

class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "A base tool"
    input_schema: Type[BaseModel] = None

    def __init__(
        self, 
        before_tool_callback: Optional[BeforeToolCallback] = None, 
        after_tool_callback: Optional[AfterToolCallback] = None
    ):
        self.before_tool_callback = before_tool_callback
        self.after_tool_callback = after_tool_callback

    # ============================================================
    # Tool helpers
    # ============================================================

    @property
    def schema(self) -> Dict:
        """Returns the JSON schema for the tool input"""
        if self.input_schema:
            return self.input_schema.model_json_schema()
        return {}

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }

    @staticmethod
    def parse_tool_args(raw_args: str | dict | None) -> dict:
        if raw_args is None:
            return {}
        if isinstance(raw_args, dict):
            return raw_args
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def build_tool_result_message(
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        }
    
    # ============================================================
    # TOOL EXECUTION with CALLBACKS
    # ============================================================

    async def execute(
            self,
            tool_call: ChatCompletionMessageToolCall,
            context: CallbackContext
        ) -> AsyncIterator[AgentEvent]:
        """
        Executes the tool with before/after callbacks and yields events.

        Args:
            args (dict): The input arguments for the tool.
            context (CallbackContext): The callback context to store intermediate results.
        
        Yields:
            AgentEvent: Events generated during tool execution and callbacks.
        """
        
        context.tool_input = None
        context.tool_result = None

        # -------------------------------------------------------------------
        # 1. Start tool execution, preprocess args for api
        # -------------------------------------------------------------------
        fn_name = tool_call.function.name
        fn_args = self.parse_tool_args(tool_call.function.arguments)

        yield AgentEvent(
            type="tool_call", 
            content=f"Calling {fn_name} with {json.dumps(fn_args)}", 
            tool_name=fn_name, 
            tool_args=fn_args,
            tool_call_id=tool_call.id
        )
        
        # -------------------------------------------------------------------
        # 2. Before Callback
        # -------------------------------------------------------------------
        if self.before_tool_callback:
            async for event in run_callback_with_events(
                callback_fn=self.before_tool_callback,
                callback_input={"tool_args": fn_args},
                context=context,
                context_attr="tool_input",
                callback_type="before_tool_callback"
            ):
                yield event
        
        effective_args = context.tool_input if context.tool_input is not None else fn_args

        # -------------------------------------------------------------------
        # 3. Run Tool - use tool's run method
        # -------------------------------------------------------------------
        try:
            if not isinstance(effective_args, dict):
                error_msg = (
                    f"Tool '{self.name}' expected arguments as a "
                    f"dict, got {type(effective_args).__name__}."
                )
                context.tool_result = error_msg
                yield AgentEvent(type="error", content=error_msg)

            
            result = await self.run(**effective_args)
            context.tool_result = str(result)

        except Exception as e:
            error_msg = f"Error executing tool '{self.name}': {type(e).__name__}: {e}"
            context.tool_result = error_msg
            yield AgentEvent(
                type="error",
                content=error_msg
            )

        # -------------------------------------------------------------------
        # 4. After Callback
        # -------------------------------------------------------------------
        if self.after_tool_callback and context.tool_result:
            async for event in run_callback_with_events(
                callback_fn=self.after_tool_callback,
                callback_input={"tool_result": context.tool_result},
                context=context,
                context_attr="tool_result",
                callback_type="after_tool_callback"
            ):
                yield event

        # -------------------------------------------------------------------
        # 5. Yield final tool result event
        # Ensure result is not None (OpenAI requirement)
        # -------------------------------------------------------------------
        if context.tool_result is None:
            context.tool_result = "Error: No result returned from tool execution."

        yield AgentEvent(
            type="tool_result", 
            content=context.tool_result, 
            tool_name=fn_name, 
            tool_call_id=tool_call.id
        )

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the tool logic"""
        pass
