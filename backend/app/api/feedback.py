from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class FeedbackRequest(BaseModel):
    session_id: str
    rating: int
    comment: str = ""

@router.post("/")
async def submit_feedback(request: FeedbackRequest):
    """Collect feedback - stub"""
    return {"status": "feedback received", "rating": request.rating}