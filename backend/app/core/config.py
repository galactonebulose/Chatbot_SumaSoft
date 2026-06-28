from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Chatbot Framework"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.1.0"
    
    # Database
    POSTGRES_URL: str = "postgresql://user:pass@localhost:5432/chatbot"
    MONGO_URL: str = "mongodb://localhost:27017/chatbot"
    QDRANT_URL: str = "http://localhost:6333"
    
    # LLM Configuration - Flexible Model Selection
    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_MODEL_NAME: str = "llama3.2:3b"
    
    # Ollama Settings
    LLM_API_BASE: str = "http://localhost:11434"   # Ollama default
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Paid / OpenAI Compatible APIs
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_COMPATIBLE_API_KEY: Optional[str] = None  # Keeping your original field
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Global settings instance
settings = Settings()