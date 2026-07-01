from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import uuid
import datetime
import json

from app.services.llm_service import LLMService
from app.core.config import settings
from app.core.db import get_db, get_mongo_db
from app.models.schemas import ToolModel, ChatSessionModel, ResourceModel
from app.services.executor import ToolExecutor
from app.api.tools import BUILTIN_TOOLS

router = APIRouter()
llm_service = LLMService()

class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    session_id: str
    tool_calls_executed: List[Dict[str, Any]] = []

def get_db_tools(db: Session) -> List[Dict[str, Any]]:
    """Helper to load all DB tools and built-ins formatted for OpenAI-compatible schema"""
    formatted = []
    
    # 1. Add built-ins
    for bt in BUILTIN_TOOLS:
        formatted.append({
            "type": "function",
            "function": {
                "name": bt["name"],
                "description": bt["description"],
                "parameters": bt["parameters"]
            }
        })
        
    # 2. Add database custom API tools
    try:
        db_tools = db.query(ToolModel).all()
        for t in db_tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
            })
    except Exception as e:
        print(f"Warning: Failed to fetch tools from database: {e}")
        
    return formatted

@router.post("/")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat endpoint supporting multi-LLM models, dynamic tool calling, and MongoDB session history"""
    
    try:
        provider = request.provider or settings.DEFAULT_LLM_PROVIDER
        model = request.model or settings.DEFAULT_MODEL_NAME
        
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Ensure session exists in PostgreSQL
        try:
            sess_in_db = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
            if not sess_in_db:
                new_sess = ChatSessionModel(id=session_id, provider=provider, model=model, user_id=request.user_id)
                db.add(new_sess)
                db.commit()
        except Exception as db_err:
            db.rollback()
            print(f"Failed to save session in PostgreSQL: {db_err}")

        # Get LLM instance
        llm = llm_service.get_provider(provider_name=provider, model_name=model)
        
        # Load conversation history from MongoDB
        mongo_db = get_mongo_db()
        history = []
        try:
            stored_msgs = list(mongo_db.chat_messages.find({"session_id": session_id}).sort("created_at", 1))
            for sm in stored_msgs:
                history.append({
                    "role": sm["role"],
                    "content": sm["content"]
                })
                # If there were assistant tool calls, we should keep them in history
                if sm.get("tool_calls"):
                    history[-1]["tool_calls"] = sm["tool_calls"]
                # If there's a tool response, map role
                if sm["role"] == "tool":
                    history[-1]["tool_call_id"] = sm.get("tool_call_id", "")
                    history[-1]["name"] = sm.get("name", "")
        except Exception as mongo_err:
            print(f"Warning: Failed to fetch history from MongoDB: {mongo_err}")
            
        # Append current user message
        user_message_dict = {"role": "user", "content": request.message}
        history.append(user_message_dict)
        
        # Log user message to MongoDB
        try:
            mongo_db.chat_messages.insert_one({
                "session_id": session_id,
                "role": "user",
                "content": request.message,
                "created_at": datetime.datetime.utcnow()
            })
        except Exception as mongo_err:
            print(f"Warning: Failed to log user message to MongoDB: {mongo_err}")
            
        # Fetch the list of uploaded resources to inform the LLM
        uploaded_files = []
        try:
            query = db.query(ResourceModel)
            if request.user_id is not None:
                query = query.filter((ResourceModel.user_id == request.user_id) | (ResourceModel.user_id.is_(None)))
            resources = query.all()
            uploaded_files = [r.filename for r in resources]
        except Exception as e:
            print(f"Warning: Failed to fetch resources in chat endpoint: {e}")

        # Load available database and built-in tools
        tools_list = get_db_tools(db)
        if not ToolExecutor.should_provide_tools(request.message):
            tools_list = None
            
        # Extract valid tool names for checking
        valid_tool_names = {t["function"]["name"] for t in tools_list} if tools_list else set()
        
        uploaded_docs_section = ""
        if uploaded_files:
            files_list_str = "\n".join([f"- {f}" for f in uploaded_files])
            uploaded_docs_section = f"""
Currently Uploaded Documents in Knowledge Base:
{files_list_str}

IMPORTANT instructions for uploaded documents:
- If the user asks a question that might refer to or be answered by the content of these uploaded documents, you MUST use the `rag_lookup` tool to query the document content before answering. Do NOT assume you know the answers to questions about these documents without searching them first.
- If the user's question relates to the topics or content of these files, call `rag_lookup` automatically.
"""

        system_prompt = f"""
You are a helpful AI assistant.

You have access to these tools:

1. calculator
   Use ONLY for mathematical computations.

2. search_web
   Use ONLY for current or real-time internet information.

3. rag_lookup
   Use ONLY for uploaded documents.
{uploaded_docs_section}
IMPORTANT:
- Most user requests DO NOT require tools.
- If you can answer directly (and the answer does not depend on the uploaded documents), do NOT call any tool.
- Never call calculator for jokes, greetings, explanations, coding, writing, or conversation.
- Never call search_web for general knowledge.
- If uploaded documents are available, and the user's query relates to their content or topics, call `rag_lookup` automatically to search the document context before answering. Always prioritize calling `rag_lookup` over `search_web` if the query topic could possibly be covered by the uploaded documents.

Before selecting a tool:

1. Can I answer directly without any external info or uploaded document context?
   If YES, answer directly.

2. Does the query require math?
   If YES, calculator.

3. Does the query relate to or require information from the uploaded documents (listed above)?
   If YES, rag_lookup.

4. Does the query require current internet information?
   If YES, search_web.
"""
        
        # Agentic Tool execution loop (max 5 iterations to prevent loops)
        loop_limit = 5
        executed_calls = []
        
        for iteration in range(loop_limit):
            # Re-assemble prompt with updated history (including tool responses)
            llm_messages = [{"role": "system", "content": system_prompt}] + history
            # Call LLM with full history and tool specifications
            response_data = await llm.generate(llm_messages, tools=tools_list)
            
            content = response_data.get("content", "")
            tool_calls = response_data.get("tool_calls", [])
            
            # Filter and validate tool calls
            valid_tool_calls = [tc for tc in tool_calls if ToolExecutor.is_valid_tool_call(tc, valid_tool_names)]
            
            # If the model generated tool calls, but none of them are valid
            if tool_calls and not valid_tool_calls:
                # Extract text content from arguments if main content is empty
                if not content:
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        name = func.get("name")
                        if not name or name not in valid_tool_names:
                            args = func.get("arguments")
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except:
                                    pass
                            if isinstance(args, dict):
                                for val in args.values():
                                    if isinstance(val, str) and len(val) > len(content):
                                        content = val
                tool_calls = []
            else:
                tool_calls = valid_tool_calls
            
            # If no tool calls, this is the final text answer
            if not tool_calls:
                # Log assistant response to MongoDB
                try:
                    mongo_db.chat_messages.insert_one({
                        "session_id": session_id,
                        "role": "assistant",
                        "content": content,
                        "created_at": datetime.datetime.utcnow()
                    })
                except Exception as mongo_err:
                    print(f"Warning: Failed to log assistant response to MongoDB: {mongo_err}")
                
                return ChatResponse(
                    response=content,
                    provider=provider,
                    model=model,
                    session_id=session_id,
                    tool_calls_executed=executed_calls
                )
            
            # Record assistant message containing tool calls in local loop history
            assistant_msg = {
                "role": "assistant",
                "content": content or None,
                "tool_calls": []
            }
            
            # Format and execute each tool call
            tool_results_to_log = []
            for tc in tool_calls:
                call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                func_name = tc["function"]["name"]
                func_args = tc["function"]["arguments"]
                
                # Format to OpenAI spec and preserve extra fields (like thought_signature)
                tc_item = {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(func_args)
                    }
                }
                for k, v in tc.items():
                    if k not in ["id", "type", "function"]:
                        tc_item[k] = v
                assistant_msg["tool_calls"].append(tc_item)
                
                # Execute tool
                print(f"Agent executing tool: {func_name} with parameters: {func_args}")
                result_text = await ToolExecutor.execute(func_name, func_args)
                
                executed_calls.append({
                    "tool_name": func_name,
                    "parameters": func_args,
                    "result": result_text
                })
                
                # Add tool message to history
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": func_name,
                    "content": result_text
                }
                tool_results_to_log.append(tool_msg)
                
            # Log assistant tool_call intent to MongoDB
            try:
                mongo_db.chat_messages.insert_one({
                    "session_id": session_id,
                    "role": "assistant",
                    "content": assistant_msg["content"],
                    "tool_calls": assistant_msg["tool_calls"],
                    "created_at": datetime.datetime.utcnow()
                })
                
                # Log tool execution outputs to MongoDB
                for tr in tool_results_to_log:
                    mongo_db.chat_messages.insert_one({
                        "session_id": session_id,
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "name": tr["name"],
                        "content": tr["content"],
                        "created_at": datetime.datetime.utcnow()
                    })
            except Exception as mongo_err:
                print(f"Warning: Failed to log intermediate states to MongoDB: {mongo_err}")
                
            # Update history list for next iteration
            history.append(assistant_msg)
            for tr in tool_results_to_log:
                history.append(tr)
                
        # If we exceeded the loop limit, return a fallback error response
        return ChatResponse(
            response="Error: Executed maximum agentic tool iterations without reaching a stable text response.",
            provider=provider,
            model=model,
            session_id=session_id,
            tool_calls_executed=executed_calls
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_sessions(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Fetch chat sessions from PostgreSQL relational table, optionally filtered by user_id"""
    try:
        query = db.query(ChatSessionModel)
        if user_id is not None:
            query = query.filter(ChatSessionModel.user_id == user_id)
        sessions = query.order_by(ChatSessionModel.created_at.desc()).all()
        return [
            {
                "id": s.id,
                "provider": s.provider,
                "model": s.model,
                "created_at": s.created_at,
                "user_id": s.user_id
            }
            for s in sessions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Fetch chat history for a session from MongoDB and format it for the UI bubble structure"""
    try:
        mongo_db = get_mongo_db()
        msgs = list(mongo_db.chat_messages.find({"session_id": session_id}).sort("created_at", 1))
        
        formatted = []
        for m in msgs:
            # Map role (user/assistant) to frontend bubble types (user/bot)
            if m["role"] == "tool":
                continue  # Tools results are mapped within their assistant calls
                
            sender = "user" if m["role"] == "user" else "bot"
            
            tool_runs = []
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    func = tc.get("function", {})
                    # Find tool result from history
                    tool_result = ""
                    tool_msg = next((x for x in msgs if x["role"] == "tool" and x.get("tool_call_id") == tc.get("id")), None)
                    if tool_msg:
                        tool_result = tool_msg.get("content", "")
                        
                    tool_runs.append({
                        "name": func.get("name"),
                        "params": func.get("arguments"),
                        "result": tool_result,
                        "status": "complete"
                    })
            
            formatted.append({
                "sender": sender,
                "text": m.get("content", "") or "",
                "toolRuns": tool_runs
            })
        return formatted
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch session messages: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a chat session from PostgreSQL and its messages from MongoDB"""
    try:
        session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            
        mongo_db = get_mongo_db()
        mongo_db.chat_messages.delete_many({"session_id": session_id})
        
        return {"status": "success", "message": f"Session {session_id} and its chat logs deleted."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")