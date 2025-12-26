from typing import AsyncIterator, List, Optional
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.agents.models import (
	AgentEvent,
	CallbackContext,
	LLMCallParams,
	LLMCallResult,
)
from app.agents.callbacks import (
	run_callback_with_events,
	BeforeModelCallback,
	AfterModelCallback,
)
from app.agents.tools.base import BaseTool
from app.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================
# LLM CALLER WITH CALLBACKS
# ============================================================


class LLM:
	"""
	Handles OpenAI LLM calls with before/after callbacks.

	Workflow:
	1. Before callback - modify params (model, messages, tools, response_format, etc.)
	2. Make LLM call
	3. After callback - modify result (parse structured output, transform content, etc.)

	Example use cases:
	- Before: Filter available tools based on context
	- Before: Inject additional system instructions
	- Before: Set response_format for structured output
	- After: Parse JSON response into typed objects
	- After: Post-process or validate the response
	"""

	def __init__(
		self,
		client: AsyncOpenAI,
		before_model_callback: Optional[BeforeModelCallback] = None,
		after_model_callback: Optional[AfterModelCallback] = None,
	):
		self.client = client
		self.before_model_callback = before_model_callback
		self.after_model_callback = after_model_callback

	async def call(
		self,
		model: str,
		messages: List[dict],
		context: Optional[CallbackContext],
		tools: Optional[List[BaseTool]] = None,
	) -> AsyncIterator[AgentEvent]:
		"""
		Makes an LLM call with before/after callbacks.

		Args:
		    params: LLM call parameters (model, messages, tools, etc.)
		    context: Callback context for storing intermediate results.
		             If None, a new context is created.

		Yields:
		    AgentEvent: Events during execution (callback events, errors)

		After completion:
		    - context.llm_params: The (possibly modified) params used for the call
		    - context.llm_result: The (possibly modified) result from the call
		"""

		# -------------------------------------------------------------------
		# 1. Initialize LLM and build tools
		# -------------------------------------------------------------------

		context.llm_params = LLMCallParams(
			model=model,
			messages=messages,
			tools=[tool.to_openai_tool() for tool in tools] if tools else None,
		)
		context.llm_result = None

		# -------------------------------------------------------------------
		# 2. BEFORE MODEL CALLBACK
		# -------------------------------------------------------------------
		if self.before_model_callback:
			async for event in run_callback_with_events(
				callback_fn=self.before_model_callback,
				callback_input={"params": context.llm_params},
				context=context,
				context_attr="llm_params",
				callback_type="before_model_callback",
			):
				yield event

		# -------------------------------------------------------------------
		# 3. MAKE LLM CALL
		# -------------------------------------------------------------------
		logger.info("Sending request to OpenAI LLM...")

		try:
			openai_kwargs = context.llm_params.to_openai_kwargs()
			response: ChatCompletion = await self.call_api(
				context, **openai_kwargs
			)

		except Exception as e:
			logger.error(f"Error in LLM call: {str(e)}")
			yield AgentEvent(type="error", content=str(e))
			return

		logger.info("Received response from OpenAI LLM.")

		# Extract response data
		message = response.choices[0].message
		result = LLMCallResult(
			content=message.content,
			tool_calls=message.tool_calls,
			raw_response=response,
		)

		# Store result in context
		context.llm_result = result

		# -------------------------------------------------------------------
		# 4. AFTER MODEL CALLBACK
		# -------------------------------------------------------------------
		if self.after_model_callback:
			async for event in run_callback_with_events(
				callback_fn=self.after_model_callback,
				callback_input={"result": context.llm_result},
				context=context,
				context_attr="llm_result",
				callback_type="after_model_callback",
			):
				yield event

		if context.llm_result is None:
			yield AgentEvent(
				type="error", content="LLM call failed without result"
			)
			return

	async def call_api(
		self, context: CallbackContext, **kwargs
	) -> LLMCallResult:
		"""
		If structured output is used, use dedicated parse method.
		Otherwise, use standard create method.
		"""

		if context.llm_params.response_format:
			return await self.client.chat.completions.parse(**kwargs)

		return await self.client.chat.completions.create(**kwargs)

	@staticmethod
	def parse_result(context: CallbackContext) -> Optional[LLMCallResult]:
		"""
		Get the LLM result from the context.
		Outputs tuple with message dict, content, and tool_calls.
		"""

		msg = {"role": "assistant"}
		content = context.llm_result.content
		tool_calls = context.llm_result.tool_calls

		if content:
			msg["content"] = content
		if tool_calls:
			msg["tool_calls"] = tool_calls

		return msg, content, tool_calls
