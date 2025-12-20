import httpx
from google.auth import default
from google.auth.transport.requests import Request
from typing import Any, Dict, Optional


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

		return await self._post(url, payload)

	# ---------------------------------------------------------------------
	# Generation with retrieval tool (Gemini / foundation model)
	# ---------------------------------------------------------------------

	async def generate_with_retrieval(
		self,
		prompt: str,
		model_id: str,
		similarity_top_k: int = 1,
		generation_method: str = "generateContent",
	) -> Dict[str, Any]:
		"""
		 Generates summary content using Gemini foundation model
		 based on retrieved contexts (chunks) from RAG Engine.
		 In addition to chunks, grounding supports and retrieval queries
		 are also provided in the response.

		Calls: POST .../models/{MODEL_ID}:{GENERATION_METHOD}

		 Result example
		 {
		 "candidates": [
		     {
		     "avgLogprobs": "number",
		     "content": {
		         "parts": [
		             {
		                 "text": "string"
		             }
		         ],
		         "role": "string"
		     },
		     "finishReason": "string",
		     "groundingMetadata": {
		         "groundingChunks": [
		         {
		             "retrievedContext": {
		             "ragChunk": {
		                 "pageSpan": {
		                     "firstPage": "integer",
		                     "lastPage": "integer"
		                 },
		                 "text": "string"
		             },
		             "text": "string",
		             "title": "string",
		             "uri": "string"
		             }
		         }
		         ],
		         "groundingSupports": [
		         {
		             "confidenceScores": [
		                 "number"
		             ],
		             "groundingChunkIndices": [
		                 "integer"
		             ],
		             "segment": {
		                 "endIndex": "integer",
		                 "startIndex": "integer",
		                 "text": "string"
		             }
		         }
		         ],
		         "retrievalQueries": [
		         "string"
		         ]
		     }
		     }
		 ],
		 "createTime": "string",
		 "modelVersion": "string",
		 "responseId": "string",
		 "usageMetadata": {
		     "candidatesTokenCount": "integer",
		     "candidatesTokensDetails": [
		     {
		         "modality": "string",
		         "tokenCount": "integer"
		     }
		     ],
		     "promptTokenCount": "integer",
		     "promptTokensDetails": [
		     {
		         "modality": "string",
		         "tokenCount": "integer"
		     }
		     ],
		     "thoughtsTokenCount": "integer",
		     "totalTokenCount": "integer",
		     "trafficType": "string"
		 }
		 }

		"""

		url = (
			f"https://{self.location}-aiplatform.googleapis.com/v1beta1/"
			f"projects/{self.project_id}/locations/{self.location}/"
			f"publishers/google/models/{model_id}:{generation_method}"
		)

		payload = {
			"contents": {"role": "user", "parts": {"text": prompt}},
			"tools": {
				"retrieval": {
					"disable_attribution": False,
					"vertex_rag_store": {
						"rag_resources": {
							"rag_corpus": f"projects/{self.project_id}/locations/{self.location}/ragCorpora/{self.rag_engine}"
						},
						"similarity_top_k": similarity_top_k,
						# "vector_distance_threshold": "0.5"
					},
				}
			},
		}

		response = await self._post(url, payload)
		return self.process_rag_response(response)

	def process_rag_response(self, response: Dict[str, Any]) -> str:
		"""
		Process the response from generate_with_retrieval
		and extract the generated content along with
		grounding information.
		"""

		candidates = response.get("candidates", [])
		if not candidates:
			return "LLM response contains no retrieved candidates."

		candidate = candidates[0]
		summary = (
			candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
		)

		grounding_metadata = candidate.get("groundingMetadata", {})
		grounding_chunks = grounding_metadata.get("groundingChunks", [])

		sources = []
		for chunk in grounding_chunks:
			source_info = {}
			retrieved_context = chunk.get("retrievedContext", {})

			source_info["title"] = retrieved_context.get("title", "No Title")
			source_info["uri"] = retrieved_context.get("uri", "No URI")
			source_info["text"] = retrieved_context.get("text", "No Text")
			source_info["page_span"] = retrieved_context.get(
				"ragChunk", {}
			).get("pageSpan", {})

			sources.append(source_info)

		supports = []
		for support in grounding_metadata.get("groundingSupports", []):
			segment = support.get("segment", {})
			support_info = {
				"text": segment.get("text", "No Text"),
				"confidence_score": support.get("confidenceScores"),
				"start_index": segment.get("startIndex"),
				"end_index": segment.get("endIndex"),
			}
			supports.append(support_info)

		output = {
			"summary": summary,
			"sources": sources,
			"supports": supports,
		}

		return output
