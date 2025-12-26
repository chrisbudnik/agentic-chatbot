from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Literal, List
from dataclasses import dataclass, field
from openai.types.chat import ChatCompletion


# ============================================================
# EVENT MODELS
# ============================================================


class AgentEvent(BaseModel):
	"""
	A single event from an agent.
	Events can be emitted by callbacks, tools, or the agent itself.
	"""

	model_config = ConfigDict(extra="allow")
	type: str
	content: str
	tool_name: Optional[str] = None
	tool_args: Optional[dict[str, Any]] = None
	tool_call_id: Optional[str] = None
	callback_type: Optional[str] = None


class CitationItem(BaseModel):
	"""
	A single citation item.
	Tools, callbacks, and the agent itself can emit citation items.

	"""

	source_type: Literal["pdf", "website", "image"]
	title: str
	url: Optional[str] = None
	text: Optional[str] = None
	page_span_start: Optional[int] = None
	page_span_end: Optional[int] = None
	gcs_path: Optional[str] = None
	source_metadata: Optional[dict[str, Any]] = None


class CitationEvent(AgentEvent):
	"""
	A list of citation items.
	Frontend is tuned to display citation items in a citation list.
	"""

	model_config = ConfigDict(extra="allow")

	type: str = "citations"
	content: str = "Citations generated."
	citations: list[CitationItem] = []


# ============================================================
# CALLBACK CONTEXT
# ============================================================


class CallbackContext:
	"""Stores final result of each callback."""

	def __init__(self) -> None:
		# Agent-level callbacks
		self.modified_input: Optional[str] = None
		self.final_answer: Optional[Any] = None

		# Tool callbacks
		self.tool_input: Optional[dict[str, Any]] = None
		self.tool_result: Optional[str] = None

		# LLM model callbacks
		self.llm_params: Optional[LLMCallParams] = None
		self.llm_result: Optional[LLMCallResult] = None

	def to_dict(self) -> dict[str, Any]:
		return dict(self.__dict__)


# ============================================================
# LLM CALLBACK MODELS
# ============================================================


@dataclass
class LLMCallParams:
	"""
	Parameters for an LLM call that can be modified by before_model callbacks.

	Callbacks can modify any of these fields to:
	- Change the model being used
	- Modify messages (system prompt, user input, etc.)
	- Filter or add tools
	- Set structured output format (response_format)
	- Adjust temperature, max_tokens, etc.
	"""

	model: str
	messages: List[dict]
	tools: Optional[List[dict]] = None
	tool_choice: Optional[str] = None
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	response_format: Optional[dict] = None
	extra_params: dict = field(default_factory=dict)

	def to_openai_kwargs(self) -> dict:
		"""Convert to kwargs dict for OpenAI API call."""
		kwargs = {
			"model": self.model,
			"messages": self.messages,
		}

		if self.tools:
			kwargs["tools"] = self.tools
			kwargs["tool_choice"] = self.tool_choice or "auto"

		if self.temperature is not None:
			kwargs["temperature"] = self.temperature

		if self.max_tokens is not None:
			kwargs["max_tokens"] = self.max_tokens

		if self.response_format is not None:
			kwargs["response_format"] = self.response_format

		# Add any extra parameters
		kwargs.update(self.extra_params)

		return kwargs


@dataclass
class LLMCallResult:
	"""
	Result from an LLM call that can be modified by after_model callbacks.

	Callbacks can modify:
	- content: The text response from the model
	- tool_calls: The tool calls requested by the model
	- parsed_output: For structured output parsing
	"""

	content: Optional[str] = None
	tool_calls: Optional[List] = None
	raw_response: Optional[ChatCompletion] = None
	parsed_output: Optional[Any] = None
