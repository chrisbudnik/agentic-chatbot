from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	PROJECT_NAME: str = "Agentic Chatbot"
	API_V1_STR: str = "/api/v1"

	# Database
	DATABASE_URL: str = "sqlite+aiosqlite:///./chatbot.db"

	OPENAI_API_KEY: str = ""

	# Configurations
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
