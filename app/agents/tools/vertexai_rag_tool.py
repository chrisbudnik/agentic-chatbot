import httpx
from pydantic import BaseModel
from google.auth import default
from google.auth.transport.requests import Request

from app.core.config import settings
from app.agents.tools.base import BaseTool


class DiscoveryEngineClient:
    """
    Use Vertex AI Discovery Engine and AI Search Application for document retrieval.
    """
    def __init__(self, app_engine: str) -> None:
        creds, project_id = default()
        auth_req = Request()
        creds.refresh(auth_req)

        self.project_id = project_id
        self.app_engine = app_engine
        self.access_token = creds.token

    def search(self, query: str):
        """
        Performs a search query against the Discovery Engine API.
        """

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/"
            f"{self.project_id}/locations/global/collections/default_collection/"
            f"engines/{self.app_engine}/servingConfigs/default_search:search"
        )

        data = {
            "query": f"{query}",
            "pageSize": 10,
            "queryExpansionSpec": {"condition": "AUTO"},
            "spellCorrectionSpec": {"mode": "AUTO"},
            "contentSearchSpec": {
                "summarySpec": {
                    "ignoreAdversarialQuery": True,
                    "includeCitations": False,
                    "summaryResultCount": 10,
                    "languageCode": "en"
                }
            }
        }
        response = httpx.post(
            url, headers=headers, json=data, timeout=httpx.Timeout(30, read=300, write=60, connect=10)
        )
        return response.json()



class VertexAIRagTool(BaseTool):
    name = "search_tool"
    description = "Searches the database for information about recommender systems."

    class Input(BaseModel):
        query: str

    input_schema = Input

    async def run(self, query: str):
        """
        Runs a search query using Vertex AI Discovery Engine.
        """
        client = DiscoveryEngineClient(app_engine=settings.VERTEXAI_APP_ENGINE_ID)
        results = client.search(query)
        return results