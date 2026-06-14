from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Chatbot Framework"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_URL: str = "postgresql://user:pass@localhost:5432/chatbot"
    MONGO_URL: str = "mongodb://localhost:27017/chatbot"
    
    # LLM / MCP
    LLM_API_BASE: str = "http://localhost:11434"  # Ollama example
    OPENAI_COMPATIBLE_API_KEY: str | None = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()