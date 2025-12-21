from typing import Literal, Optional, Any
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	# ------------------------------------------------------------
	# Project Settings
	# ------------------------------------------------------------
	PROJECT_NAME: str = "Agentic Chatbot"
	API_V1_STR: str = "/api/v1"
	LOG_LEVEL: str = "INFO"
	LOG_MODE: Literal["standard", "json"] = "standard"
	DATABASE_URL: str = "sqlite+aiosqlite:///./chatbot.db"

	# ------------------------------------------------------------
	# OpenAI Settings
	# ------------------------------------------------------------
	OPENAI_API_KEY: str = ""

	# ------------------------------------------------------------
	# Google Cloud Platform & Vertex AI RAG
	# ------------------------------------------------------------
	GCP_PROJECT_ID: str = Field(
		default="",
		validation_alias=AliasChoices(
			"GCP_PROJECT_ID", "gcp_project_id", "GCO_PROJECT_ID"
		),
	)
	GCP_CREDENTIALS_JSON: Optional[dict[str, Any]] = None

	VERTEXAI_SEARCH_APPLICATION_ID: str = ""
	VERTEXAI_RAG_ENGINE_ID: str = ""
	VERTEXAI_RAG_ENGINE_REGION: str = ""

	# Configurations
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)


settings = Settings()
