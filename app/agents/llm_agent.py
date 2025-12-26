from typing import List, AsyncIterator, Optional
from openai import AsyncOpenAI
from app.agents.base import BaseAgent
from app.agents.tools.base import BaseTool
from app.core.config import settings
from app.agents.callbacks import (
	BeforeModelCallback,
	AfterModelCallback,
	BeforeAgentCallback,
	AfterAgentCallback,
)
from app.agents.models import AgentEvent, CallbackContext
from app.agents.llm import LLM
from app.core.logging import get_logger


logger = get_logger(__name__)


class LLMAgent(BaseAgent):
	def __init__(
		self,
		name: str,
		description: str,
		system_prompt: str,
		tools: Optional[List[BaseTool]] = None,
		model: str = "gpt-4.1",
		before_agent_callback: Optional[BeforeAgentCallback] = None,
		after_agent_callback: Optional[AfterAgentCallback] = None,
		before_model_callback: Optional[BeforeModelCallback] = None,
		after_model_callback: Optional[AfterModelCallback] = None,
	):
		super().__init__(
			name=name,
			description=description,
			system_prompt=system_prompt,
			tools=tools,
			model=model,
			before_agent_callback=before_agent_callback,
			after_agent_callback=after_agent_callback,
		)
		self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

		self.llm = LLM(
			client=self.client,
			before_model_callback=before_model_callback,
			after_model_callback=after_model_callback,
		)

	async def _process_turn(
		self,
		history: List[dict],
		user_input: str,
		callback_context: CallbackContext,
	) -> AsyncIterator[AgentEvent]:
		"""
		Process a single turn of the agent's operation using OpenAI's LLM with tool use.

		Args:
			history (List[dict]): The conversation history in OpenAI message format.
			user_input (str): The latest user input to process.
			callback_context (CallbackContext): Context for callbacks during tool execution.

		Yields:
			AsyncIterator[AgentEvent]: An asynchronous iterator of AgentEvents representing
		"""

		# -------------------------------------------------------------------
		# 1. Prepare Message History
		# -------------------------------------------------------------------
		messages = [
			{
				"role": "system",
				"content": self.system_prompt,
			}
		]
		messages.extend(history)
		messages.append({"role": "user", "content": user_input})

		# # -------------------------------------------------------------------
		# # 2. Prepare Tools
		# # -------------------------------------------------------------------
		# openai_tools = (
		# 	[t.to_openai_tool() for t in self.tools.values()]
		# 	if self.tools
		# 	else None
		# )
		logger.info(f"LLMAgent with message: {user_input}")

		# -------------------------------------------------------------------
		# 3. ReAct / Tool-Use Loop
		# - handle LLM response,
		# - execute tools,
		# - feed tool results back to LLM history
		# -------------------------------------------------------------------
		while True:
			# Make LLM call (pass tools as list, not dict)

			async for event in self.llm.call(
				self.model, messages, callback_context, self.tools
			):
				yield event

			msg, content, tool_calls = self.llm.parse_result(callback_context)

			# # Get the result from the LLM call
			# result = callback_context.llm_result

			# content = result.content
			# tool_calls = result.tool_calls

			# # Build message dict for history
			# msg_dict = {"role": "assistant"}
			# if content:
			# 	msg_dict["content"] = content
			# if tool_calls:
			# 	msg_dict["tool_calls"] = tool_calls

			messages.append(msg)

			# If no tool calls, we have the final answer
			if not tool_calls:
				yield AgentEvent(type="answer", content=content)
				break

			# If there's content with tool calls, it's a "thought"
			if content:
				yield AgentEvent(type="thought", content=content)

			# Execute each tool call
			for tool_call in tool_calls:
				logger.info(f"Executing tool: {tool_call.function.name}")

				# New context for each tool - avoid race conditions
				tool_context: CallbackContext = CallbackContext()

				tool = self.get_tool(tool_call.function.name)

				async for event in tool.execute(tool_call, tool_context):
					yield event
				tool_result = tool_context.tool_result

				messages.append(
					BaseTool.build_tool_result_message(
						tool_call.id,
						tool_call.function.name,
						tool_result
						or "Error: Tool failed without returning a result.",
					)
				)
