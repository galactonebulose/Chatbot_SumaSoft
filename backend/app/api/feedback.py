from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.schemas import FeedbackModel

router = APIRouter()

class FeedbackRequest(BaseModel):
    session_id: str
    rating: int
    comment: str = ""

@router.post("/")
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Store user rating and comment feedback in PostgreSQL"""
    try:
        new_feedback = FeedbackModel(
            session_id=request.session_id,
            rating=request.rating,
            comment=request.comment
        )
        db.add(new_feedback)
        db.commit()
        return {"status": "success", "rating": request.rating, "session_id": request.session_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")