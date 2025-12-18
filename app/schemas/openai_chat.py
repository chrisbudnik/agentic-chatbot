from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class OpenAIToolFunction(BaseModel):
	name: str
	# OpenAI expects a JSON string in `arguments`
	arguments: str


class OpenAIToolCall(BaseModel):
	id: str
	type: Literal["function"] = "function"
	function: OpenAIToolFunction


class OpenAIChatMessage(BaseModel):
	"""
	A minimal, OpenAI-compatible chat message schema.

	We keep this intentionally narrow: it only models the fields we actually
	construct/persist in this app (user/assistant/tool messages + tool calls).
	"""

	role: Literal["system", "user", "assistant", "tool"]
	content: Optional[str] = None

	# tool message fields
	tool_call_id: Optional[str] = None
	name: Optional[str] = None

	# assistant tool calling fields
	tool_calls: Optional[List[OpenAIToolCall]] = None

	# allow extra keys for forward-compat (but we only emit known ones)
	model_config = {"extra": "allow"}

	def to_openai_dict(self) -> Dict[str, Any]:
		"""
		Dump to the dict shape expected by OpenAI's chat.completions API,
		excluding None fields.
		"""
		return self.model_dump(exclude_none=True)
