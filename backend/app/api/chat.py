from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.llm_service import LLMService
from app.core.config import settings

router = APIRouter()

llm_service = LLMService()

class ChatRequest(BaseModel):
    message: str
    provider: str = None
    model: str = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    session_id: Optional[str] = None

@router.post("/")
async def chat_endpoint(request: ChatRequest):
    """Basic Chat endpoint using configurable LLM"""
    
    try:
        provider = request.provider or settings.DEFAULT_LLM_PROVIDER
        model = request.model or settings.DEFAULT_MODEL_NAME

        # Get LLM instance
        llm = llm_service.get_provider(provider_name=provider, model_name=model)

        # Generate response
        response_text = await llm.generate(request.message)

        return ChatResponse(
            response=response_text,
            provider=provider,
            model=model,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))