from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	PROJECT_NAME: str = "Agentic Chatbot"
	API_V1_STR: str = "/api/v1"

	# Database
	DATABASE_URL: str = "sqlite+aiosqlite:///./chatbot.db"

	OPENAI_API_KEY: str = ""

	# Google Cloud Platform & Vertex AI RAG
	GCP_PROJECT_ID: str = Field(
		default="",
		validation_alias=AliasChoices("GCP_PROJECT_ID", "gcp_project_id", "GCO_PROJECT_ID"),
	)
	VERTEXAI_APP_ENGINE_ID: str = ""

	# Configurations
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)


settings = Settings()
