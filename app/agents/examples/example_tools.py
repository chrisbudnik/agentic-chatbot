from pydantic import BaseModel
from app.agents.tools.base import BaseTool
import asyncio


class DummySearchTool(BaseTool):
	name = "search_tool"
	description = "Searches the database for information."

	class Input(BaseModel):
		query: str

	input_schema = Input

	async def run(self, query: str):
		await asyncio.sleep(10)  # Simulate a delay
		return (
			f"Results for '{query}': Found 3 documents related to this topic."
		)
	

