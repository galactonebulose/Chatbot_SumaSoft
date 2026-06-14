from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    # Add context, tools, etc. later

class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: List = []

@router.post("/")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint - stub for Week 1"""
    # TODO: Integrate LLM + tool calling + RAG
    return ChatResponse(
        response=f"Echo: {request.message}. (Skeleton - LLM integration coming in Week 2)",
        session_id=request.session_id or "default",
        tool_calls=[]
    )