from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Type, Dict


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "A base tool"
    input_schema: Type[BaseModel] = None

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the tool logic"""
        pass

    @property
    def schema(self) -> Dict:
        """Returns the JSON schema for the tool input"""
        if self.input_schema:
            return self.input_schema.model_json_schema()
        return {}
