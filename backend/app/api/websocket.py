from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import json
import uuid
import datetime
from sqlalchemy.orm import Session

from app.services.llm_service import LLMService
from app.core.db import SessionLocal, get_mongo_db
from app.models.schemas import ToolModel, ChatSessionModel, ResourceModel
from app.services.executor import ToolExecutor
from app.api.chat import get_db_tools

router = APIRouter()
llm_service = LLMService()

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    # Establish a clean local DB session for PostgreSQL
    db: Session = SessionLocal()
    mongo_db = get_mongo_db()
    
    current_provider = "ollama"
    current_model = "llama3.2:3b"
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            user_message = payload.get("message", "").strip()
            if not user_message:
                continue
                
            provider = payload.get("provider", current_provider)
            model = payload.get("model", current_model)
            session_id = payload.get("session_id") or session_id
            
            current_provider = provider
            current_model = model
            
            # Extract user_id from payload
            user_id = payload.get("user_id")
            
            # Generate session ID if not set
            session_created = False
            if not session_id:
                session_id = str(uuid.uuid4())
                session_created = True
                
            # Ensure session exists in PostgreSQL
            try:
                sess_in_db = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
                if not sess_in_db:
                    new_sess = ChatSessionModel(id=session_id, provider=provider, model=model, user_id=user_id)
                    db.add(new_sess)
                    db.commit()
                    session_created = True
            except Exception as e:
                db.rollback()
                print(f"WS: Failed to save session in SQL: {e}")
                session_created = True

            if session_created:
                # Broadcast the newly initialized session_id
                await websocket.send_json({"type": "session_created", "session_id": session_id})

            # 1. Fetch Chat History from MongoDB
            history = []
            try:
                stored_msgs = list(mongo_db.chat_messages.find({"session_id": session_id}).sort("created_at", 1))
                for sm in stored_msgs:
                    history.append({
                        "role": sm["role"],
                        "content": sm["content"]
                    })
                    if sm.get("tool_calls"):
                        history[-1]["tool_calls"] = sm["tool_calls"]
                    if sm["role"] == "tool":
                        history[-1]["tool_call_id"] = sm.get("tool_call_id", "")
                        history[-1]["name"] = sm.get("name", "")
            except Exception as e:
                print(f"WS: History query failed: {e}")

            # 2. Append User Message
            history.append({"role": "user", "content": user_message})
            try:
                mongo_db.chat_messages.insert_one({
                    "session_id": session_id,
                    "role": "user",
                    "content": user_message,
                    "created_at": datetime.datetime.utcnow()
                })
            except Exception as e:
                print(f"WS: Message logging failed: {e}")

            # Send thinking feedback to frontend
            await websocket.send_json({"type": "thinking", "content": "Thinking..."})

            # Get LLM instance
            llm = llm_service.get_provider(provider_name=provider, model_name=model)
            # Fetch the list of uploaded resources to inform the LLM
            uploaded_files = []
            try:
                query = db.query(ResourceModel)
                if user_id is not None:
                    query = query.filter((ResourceModel.user_id == user_id) | (ResourceModel.user_id.is_(None)))
                resources = query.all()
                uploaded_files = [r.filename for r in resources]
            except Exception as e:
                print(f"WS: Failed to fetch resources in websocket: {e}")

            # Load available database and built-in tools
            tools_list = get_db_tools(db)
            if not ToolExecutor.should_provide_tools(user_message):
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
            
            # Execution loop (max 5 iterations)
            loop_limit = 5
            loop_index = 0
            
            while loop_index < loop_limit:
                loop_index += 1
                
                # Re-assemble prompt with updated history (including tool responses)
                llm_messages = [{"role": "system", "content": system_prompt}] + history
                
                # Active streaming parameters
                active_text_response = ""
                pending_tool_calls = []
                
                # Run the stream generator
                async for chunk in llm.stream_generate(llm_messages, tools=tools_list):
                    # Check text content
                    content = chunk.get("content", "")
                    if content:
                        active_text_response += content
                        # Broadcast token
                        await websocket.send_json({"type": "token", "content": content})
                        
                    # Check tool calls
                    tool_calls = chunk.get("tool_calls", [])
                    if tool_calls:
                        pending_tool_calls.extend(tool_calls)

                # Filter and validate pending tool calls
                valid_pending_tool_calls = [tc for tc in pending_tool_calls if ToolExecutor.is_valid_tool_call(tc, valid_tool_names)]
                
                # If there were tool calls, but none of them are valid:
                if pending_tool_calls and not valid_pending_tool_calls:
                    # Extract text content from arguments if active_text_response is empty
                    if not active_text_response:
                        for tc in pending_tool_calls:
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
                                        if isinstance(val, str) and len(val) > len(active_text_response):
                                            active_text_response = val
                                            # Broadcast recovered text as a token
                                            await websocket.send_json({"type": "token", "content": val})
                    pending_tool_calls = []
                else:
                    pending_tool_calls = valid_pending_tool_calls

                # Case A: Model requested tool calls
                if pending_tool_calls:
                    assistant_msg = {
                        "role": "assistant",
                        "content": active_text_response or None,
                        "tool_calls": []
                    }
                    
                    tool_results_to_log = []
                    
                    # Execute each tool call
                    for tc in pending_tool_calls:
                        call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                        func_name = tc["function"]["name"]
                        func_args = tc["function"]["arguments"]
                        
                        # Support parsing stringified arguments
                        if isinstance(func_args, str):
                            try:
                                func_args = json.loads(func_args)
                            except:
                                pass
                                
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
                        
                        # Notify frontend that tool execution started
                        await websocket.send_json({
                            "type": "tool_call",
                            "tool_name": func_name,
                            "parameters": func_args
                        })
                        
                        # Execute
                        print(f"WS Executing: {func_name}({func_args})")
                        result_text = await ToolExecutor.execute(func_name, func_args)
                        
                        # Notify frontend of result
                        await websocket.send_json({
                            "type": "tool_result",
                            "tool_name": func_name,
                            "result": result_text
                        })
                        
                        tool_msg = {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": func_name,
                            "content": result_text
                        }
                        tool_results_to_log.append(tool_msg)

                    # Log to MongoDB
                    try:
                        mongo_db.chat_messages.insert_one({
                            "session_id": session_id,
                            "role": "assistant",
                            "content": assistant_msg["content"],
                            "tool_calls": assistant_msg["tool_calls"],
                            "created_at": datetime.datetime.utcnow()
                        })
                        for tr in tool_results_to_log:
                            mongo_db.chat_messages.insert_one({
                                "session_id": session_id,
                                "role": "tool",
                                "tool_call_id": tr["tool_call_id"],
                                "name": tr["name"],
                                "content": tr["content"],
                                "created_at": datetime.datetime.utcnow()
                            })
                    except Exception as e:
                        print(f"WS: Database logging of tool steps failed: {e}")

                    # Update history list and loop back
                    history.append(assistant_msg)
                    for tr in tool_results_to_log:
                        history.append(tr)
                        
                    # Send thinking state again for next turn
                    await websocket.send_json({"type": "thinking", "content": "Thinking (multi-turn)..."})
                    continue

                # Case B: Final text generation completed (no tool calls)
                else:
                    # Log the final response message
                    try:
                        mongo_db.chat_messages.insert_one({
                            "session_id": session_id,
                            "role": "assistant",
                            "content": active_text_response,
                            "created_at": datetime.datetime.utcnow()
                        })
                    except Exception as e:
                        print(f"WS: Log final message failed: {e}")
                        
                    await websocket.send_json({
                        "type": "complete",
                        "content": active_text_response,
                        "model": model,
                        "provider": provider,
                        "session_id": session_id
                    })
                    break

            if loop_index >= loop_limit:
                await websocket.send_json({
                    "type": "error",
                    "content": "Error: Exceeded agentic loop iteration limit during multi-turn streaming."
                })

    except WebSocketDisconnect:
        print(f"WS Client disconnected from session {session_id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"WebSocket General Error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass
    finally:
        db.close()