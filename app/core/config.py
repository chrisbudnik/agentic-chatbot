from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic Chatbot"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./chatbot.db" # Default to SQLite for easy local dev, can switch to Postgres
    
    # LLM (Optional for now, but good to have ready)
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
