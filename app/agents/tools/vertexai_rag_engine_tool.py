import httpx
from google.auth import default
from google.auth.transport.requests import Request
from typing import Any, Dict, Optional
from pydantic import BaseModel
from typing import AsyncIterator
from app.agents.tools.base import BaseTool
from app.agents.models import CallbackContext, AgentEvent


class RagEngineClient:
	"""
	Client for Vertex AI RAG:
	- RAG Engine retrieve
	- retrieveContexts
	- Generation with retrieval tool

	Docs:
	https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/rag-api#rest_2
	"""

	def __init__(
		self,
		*,
		rag_engine: str,
		location: str,
		project_id: Optional[str] = None,
	) -> None:
		creds, default_project_id = default()
		auth_req = Request()
		creds.refresh(auth_req)

		self.project_id = project_id or default_project_id
		self.location = location
		self.rag_engine = rag_engine
		self.access_token = creds.token

		self.httpx_client = httpx.AsyncClient(
			timeout=httpx.Timeout(30, read=300, write=60, connect=10)
		)

	async def _post(self, url: str, payload: dict) -> Dict[str, Any]:
		"""Helper method to make authenticated POST requests."""

		headers = {
			"Authorization": f"Bearer {self.access_token}",
			"Content-Type": "application/json; charset=utf-8",
		}

		response = await self.httpx_client.post(
			url, json=payload, headers=headers
		)
		response.raise_for_status()
		return response.json()

	# ---------------------------------------------------------------------
	# Vertex AI Rag Engie: retrieveContexts
	# ---------------------------------------------------------------------

	async def retrieve_contexts(
		self,
		text: str,
		similarity_top_k: int = 1,
	) -> Dict[str, Any]:
		"""
		Retrives contexts (chunks sorted by similarity)
		from the RAG Engine without model summary generations.
		Calls: POST .../locations/{location}:retrieveContexts

		Args:
		    text (str): The input text query.
		    similarity_top_k (int): Number of top similar contexts to retrieve.

		Output schema:
		{
		"contexts": {
		    "contexts": [
		    {
		        "chunk": {
		        "pageSpan": {
		            "firstPage": "integer",
		            "lastPage": "integer"
		        },
		        "text": "string"
		        },
		        "distance": "number",
		        "score": "number",
		        "sourceDisplayName": "string",
		        "sourceUri": "string",
		        "text": "string"
		    }
		    ]
		}
		}
		"""

		url = (
			f"https://{self.location}-aiplatform.googleapis.com/v1beta1/"
			f"projects/{self.project_id}/locations/{self.location}:retrieveContexts"
		)

		payload = {
			"vertex_rag_store": {
				"rag_resources": {
					"rag_corpus": f"projects/{self.project_id}/locations/{self.location}/ragCorpora/{self.rag_engine}",
				},
				# "vector_distance_threshold": 0.5,
			},
			"query": {
				"text": text,
				"similarity_top_k": similarity_top_k,
			},
		}

		response = await self._post(url, payload)
		return self.process_context_retrieval(response)

	def process_context_retrieval(self, response: Dict[str, Any]) -> str:
		"""
		Process the response from retrieve_contexts
		and extract the generated content along with
		grounding information.
		"""

		contexts = response.get("contexts", {}).get("contexts", [])
		if not contexts:
			return "No contexts retrieved from RAG Engine."

		results = []
		for context in contexts:
			result = {
				"text": context.get("text", "No Text"),
				"source_name": context.get(
					"sourceDisplayName", "No Source Name"
				),
				"source_uri": context.get("sourceUri", "No Source URI"),
				"page_span": context.get("chunk", {}).get("pageSpan", {}),
			}
			results.append(result)

		return results


class VertexAIRagEngineTool(BaseTool):
	name = "search_tool"
	description = (
		"Searches the database for information about recommender systems."
	)

	class Input(BaseModel):
		query: str

	input_schema = Input

	async def run(
		self, context: CallbackContext, query: str
	) -> AsyncIterator[AgentEvent]:
		"""
		Runs a search query using Vertex AI Discovery Engine.
		"""
		client = RagEngineClient(
			rag_engine="2305843009213693952",
			location="europe-west1",
		)
		results = await client.retrieve_contexts(query, similarity_top_k=3)
		context.tool_result = str(results)

		citations = [item["source_name"] for item in results]

		yield AgentEvent(
			type="citations",
			content=f"Search completed. Retrieved {len(results)} contexts.",
			citations=citations,
		)
