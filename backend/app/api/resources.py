from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

router = APIRouter()

@router.post("/upload")
async def upload_resource(file: UploadFile = File(...)):
    """Upload PDF, DOCX, etc. - stub for Week 3"""
    return {"filename": file.filename, "status": "uploaded (stub)"}