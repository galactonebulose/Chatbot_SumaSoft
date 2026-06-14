from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.core.config import Settings
from app.api import chat, tools, resources, feedback

load_dotenv()

app = FastAPI(
    title="Chatbot Framework API",
    description="Backend for MCP-enabled Chatbot with Tool Calling and RAG",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(tools.router, prefix="/tool", tags=["Tools"])
app.include_router(resources.router, prefix="/resource", tags=["Resources"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])

@app.get("/")
async def root():
    return {"message": "Chatbot Framework API is running. Visit /docs for Swagger UI"}

@app.get("/health")
async def health():
    return {"status": "healthy"}