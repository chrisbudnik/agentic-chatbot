from pydantic import BaseModel, Field
from typing import List, Optional



# ============================================================
# EVENT MODEL
# ============================================================

class AgentEvent(BaseModel):
    type: str
    content: str
    tool_name: str = None
    tool_args: dict = None
    tool_call_id: str = None
    callback_type: str = None


# ============================================================
# COLLECTOR
# ============================================================
class CallbackContext:
    """Stores final result of each callback."""

    def __init__(self):
        self.modified_input: Optional[str] = None
        self.final_answer: Optional[str] = None
        self.tool_input: Optional[dict] = None
        self.tool_result: Optional[str] = None
    
    def to_dict(self) -> dict:
        return dict(self.__dict__)