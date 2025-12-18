from typing import List, AsyncIterator, Optional
from openai import AsyncOpenAI
from app.agents.base import BaseAgent, AgentEvent
from app.agents.tools.base import BaseTool
from app.core.config import settings
from app.agents.models import CallbackContext
from app.core.logging import get_logger


logger = get_logger(__name__)


class LLMAgent(BaseAgent):
	def __init__(
		self,
		name: str,
		description: str,
		tools: Optional[List[BaseTool]] = None,
		model: str = "gpt-4.1",
		before_agent_callback=None,
		after_agent_callback=None,
	):
		super().__init__(
			name=name,
			description=description,
			tools=tools,
			model=model,
			before_agent_callback=before_agent_callback,
			after_agent_callback=after_agent_callback,
		)
		self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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
		# 1. Prepare Messages
		# -------------------------------------------------------------------
		messages = [
			{
				"role": "system",
				"content": "You are a helpful assistant. Use tools when necessary.",
			}
		]
		messages.extend(history)
		messages.append({"role": "user", "content": user_input})

		# -------------------------------------------------------------------
		# 2. Prepare Tools
		# -------------------------------------------------------------------
		openai_tools = (
			[t.to_openai_tool() for t in self.tools.values()]
			if self.tools
			else None
		)

		logger.info(f"LLMAgent with message: {user_input}")

		# -------------------------------------------------------------------
		# 3. ReAct / Tool-Use Loop
		# - handle LLM response,
		# - execute tools,
		# - feed tool results back to LLM history
		# -------------------------------------------------------------------
		while True:
			logger.info("Sending request to OpenAI LLM...")
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

			logger.info("Received response from OpenAI LLM.")

			message = response.choices[0].message
			content = message.content
			tool_calls = message.tool_calls

			msg_dict = {"role": "assistant"}
			if content:
				msg_dict["content"] = content
			if tool_calls:
				msg_dict["tool_calls"] = tool_calls

			messages.append(msg_dict)

			if not tool_calls:
				yield AgentEvent(type="answer", content=content)
				break

			if content:
				yield AgentEvent(type="thought", content=content)

			for tool_call in tool_calls:
				logger.info(f"Executing tool: {tool_call.function.name}")

				# new context for each tool - avoid race conditions
				tool_context: CallbackContext = CallbackContext()
				tool = self.tools.get(tool_call.function.name)

				if tool:
					async for event in tool.execute(tool_call, tool_context):
						yield event
					tool_result = tool_context.tool_result
				else:
					# this error practically never happens for newer models
					tool_result = (
						f"Error: Tool '{tool_call.function.name}' not found."
					)

				messages.append(
					BaseTool.build_tool_result_message(
						tool_call.id,
						tool_call.function.name,
						tool_result
						or "Error: Tool failed without returning a result.",
					)
				)
