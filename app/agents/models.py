from pydantic import BaseModel
from typing import Optional, Any


# ============================================================
# EVENT MODEL
# ============================================================


class AgentEvent(BaseModel):
	type: str
	content: str
	tool_name: Optional[str] = None
	tool_args: Optional[dict[str, Any]] = None
	tool_call_id: Optional[str] = None
	callback_type: Optional[str] = None


# ============================================================
# COLLECTOR
# ============================================================
class CallbackContext:
	"""Stores final result of each callback."""

	def __init__(self):
		self.modified_input: Optional[str] = None
		# After-agent callbacks may choose to store a modified "final answer"
		# (either as an AgentEvent or as raw content, depending on the demo).
		self.final_answer: Optional[Any] = None
		self.tool_input: Optional[dict[str, Any]] = None
		self.tool_result: Optional[str] = None

	def to_dict(self) -> dict:
		return dict(self.__dict__)
