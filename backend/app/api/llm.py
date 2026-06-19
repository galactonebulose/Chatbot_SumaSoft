from fastapi import APIRouter
from app.core.config import settings
from app.services.llm_service import LLMService

#This will show all the available models and APIs that can be used.

router = APIRouter(prefix="/llm", tags=["LLM"])

llm_service = LLMService()

@router.get("/models")
async def list_available_models():
    """Return all available LLM providers and models"""
    return {
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_model": settings.DEFAULT_MODEL_NAME,
        "available_providers": llm_service.get_available_providers(),
        "models": llm_service.get_available_models(),   # We'll add this method next
        "note": "You can switch provider/model in WebSocket or future REST calls"
    }


@router.get("/config")
async def get_llm_config():
    """Return current LLM configuration"""
    return {
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_model": settings.DEFAULT_MODEL_NAME,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "has_groq_key": bool(settings.GROQ_API_KEY)
    }