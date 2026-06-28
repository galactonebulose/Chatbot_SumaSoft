from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.schemas import ToolModel
from app.services.executor import ToolExecutor

router = APIRouter()

class ToolRegisterRequest(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    type: str = "api"
    url: Optional[str] = None
    method: Optional[str] = "GET"
    headers: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None

class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

# Predefined built-in tools returned alongside DB tools
BUILTIN_TOOLS = [
    {
        "name": "calculator",
        "description": "Safely evaluates simple mathematical expressions (+, -, *, /, parentheses).",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The arithmetic expression to evaluate, e.g., '2 + 2' or '(3 * 4) / 2'"
                }
            },
            "required": ["expression"]
        },
        "type": "builtin"
    },
    {
        "name": "search_web",
        "description": "Mocks a web search to fetch summaries on a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The web search query"
                }
            },
            "required": ["query"]
        },
        "type": "builtin"
    },
    {
        "name": "rag_lookup",
        "description": "Queries the local document knowledge base using vector semantic search.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to retrieve contextual fragments from PDF, DOCX, CSV, TXT"
                }
            },
            "required": ["query"]
        },
        "type": "builtin"
    }
]

@router.get("/")
async def list_tools(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all registered tools (both built-in and dynamic custom API tools), optionally filtered by user_id"""
    try:
        query = db.query(ToolModel)
        if user_id is not None:
            # Show system-wide tools (user_id is None) and user-specific tools
            query = query.filter((ToolModel.user_id == user_id) | (ToolModel.user_id.is_(None)))
        db_tools = query.all()
        formatted_db_tools = []
        for t in db_tools:
            formatted_db_tools.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "type": t.type,
                "url": t.url,
                "method": t.method,
                "headers": t.headers,
                "user_id": t.user_id
            })
        return BUILTIN_TOOLS + formatted_db_tools
    except Exception as e:
        # Fall back to built-ins if DB is uninitialized or fails
        print(f"Warning: Tool DB listing failed, returning built-ins: {e}")
        return BUILTIN_TOOLS

@router.post("/register")
async def register_tool(request: ToolRegisterRequest, db: Session = Depends(get_db)):
    """Register a new dynamic API tool or update if it exists"""
    if request.name in ["calculator", "search_web", "rag_lookup"]:
        raise HTTPException(status_code=400, detail="Cannot override system built-in tools")
        
    try:
        existing = db.query(ToolModel).filter(ToolModel.name == request.name).first()
        if existing:
            existing.description = request.description
            existing.parameters = request.parameters
            existing.type = request.type
            existing.url = request.url
            existing.method = request.method
            existing.headers = request.headers
            existing.user_id = request.user_id
        else:
            new_tool = ToolModel(
                name=request.name,
                description=request.description,
                parameters=request.parameters,
                type=request.type,
                url=request.url,
                method=request.method,
                headers=request.headers,
                user_id=request.user_id
            )
            db.add(new_tool)
        db.commit()
        return {"status": "registered", "tool": request.name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to register tool: {str(e)}")

@router.delete("/{name}")
async def delete_tool(name: str, db: Session = Depends(get_db)):
    """Delete a dynamic tool by name"""
    if name in ["calculator", "search_web", "rag_lookup"]:
        raise HTTPException(status_code=400, detail="Cannot delete built-in tools")
        
    try:
        tool = db.query(ToolModel).filter(ToolModel.name == name).first()
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
        db.delete(tool)
        db.commit()
        return {"status": "deleted", "tool": name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete tool: {str(e)}")

@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a registered tool (built-in or custom API tool)"""
    try:
        result = await ToolExecutor.execute(request.tool_name, request.parameters)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))