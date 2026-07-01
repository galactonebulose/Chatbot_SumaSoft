from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.llm_service import LLMService
from app.core.db import get_db
from app.models.schemas import LLMConfigModel

router = APIRouter(prefix="/llm", tags=["LLM"])
llm_service = LLMService()

class LLMConfigRequest(BaseModel):
    provider: str
    api_key: str

@router.get("/models")
async def list_available_models():
    """Return all available LLM providers and models"""
    return {
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_model": settings.DEFAULT_MODEL_NAME,
        "available_providers": llm_service.get_available_providers(),
        "models": llm_service.get_available_models(),
        "note": "You can switch provider/model in WebSocket or future REST calls"
    }

@router.get("/config")
async def get_llm_config(db: Session = Depends(get_db)):
    """Return current LLM configuration state"""
    try:
        openai_key = db.query(LLMConfigModel).filter(LLMConfigModel.provider == "openai").first()
        anthropic_key = db.query(LLMConfigModel).filter(LLMConfigModel.provider == "anthropic").first()
        gemini_key = db.query(LLMConfigModel).filter(LLMConfigModel.provider == "gemini").first()
        has_openai = bool(openai_key and openai_key.api_key)
        has_anthropic = bool(anthropic_key and anthropic_key.api_key)
        has_gemini = bool(gemini_key and gemini_key.api_key)
    except Exception as e:
        print(f"Database error in get_llm_config: {e}")
        has_openai = False
        has_anthropic = False
        has_gemini = False
        
    return {
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_model": settings.DEFAULT_MODEL_NAME,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "has_openai_key": has_openai,
        "has_anthropic_key": has_anthropic,
        "has_gemini_key": has_gemini,
    }

@router.post("/config")
async def save_llm_config(request: LLMConfigRequest, db: Session = Depends(get_db)):
    """Save or update API key for OpenAI, Anthropic, or Gemini"""
    provider = request.provider.lower()
    if provider not in ["openai", "anthropic", "gemini"]:
        raise HTTPException(status_code=400, detail="Invalid provider. Supported: openai, anthropic, gemini")
    
    try:
        config = db.query(LLMConfigModel).filter(LLMConfigModel.provider == provider).first()
        if config:
            config.api_key = request.api_key
        else:
            config = LLMConfigModel(provider=provider, api_key=request.api_key)
            db.add(config)
        db.commit()
        return {"status": "success", "message": f"API key for {provider} configured successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save LLM configuration: {str(e)}")