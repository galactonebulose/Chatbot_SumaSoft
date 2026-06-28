from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.api.websocket import router as websocket_router
from app.core.config import Settings
from app.api import chat, tools, resources, feedback, users
from app.api import llm
from fastapi.staticfiles import StaticFiles

load_dotenv()

# Initialize DB tables on startup
try:
    from app.core.db import engine
    from app.models.base import Base
    from app.models import schemas
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
except Exception as db_init_err:
    print(f"Warning: Relational database table initialization skipped/failed: {db_init_err}")

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
# Mount static files (frontend)
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend"
)
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
else:
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(users.router, prefix="/user", tags=["Users"])
app.include_router(tools.router, prefix="/tool", tags=["Tools"])
app.include_router(resources.router, prefix="/resource", tags=["Resources"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
# WebSocket Router
app.include_router(websocket_router, prefix="/chat", tags=["WebSocket"])
# LLM Configuration & Model Selection
app.include_router(llm.router, prefix="/api/v1", tags=["LLM"])

@app.get("/")
async def root():
    return {"message": "Chatbot Framework API is running. Visit /docs for Swagger UI"}

@app.get("/health")
async def health():
    return {"status": "healthy"}