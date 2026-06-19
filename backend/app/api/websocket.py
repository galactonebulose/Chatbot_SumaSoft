from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import json

from app.services.llm_service import LLMService

router = APIRouter()

llm_service = LLMService()

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    current_provider = "ollama"
    current_model = "llama3.2:3b"
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            user_message = message.get("message", "")
            provider = message.get("provider", current_provider)
            model = message.get("model", current_model)
            
            current_provider = provider
            current_model = model

            llm = llm_service.get_provider(provider_name=provider, model_name=model)

            await websocket.send_json({"type": "thinking", "content": "Thinking..."})

            full_response = ""
            async for token in llm.stream_generate(user_message):
                full_response += token
                await websocket.send_json({
                    "type": "token",
                    "content": token
                })
            
            await websocket.send_json({
                "type": "complete",
                "content": full_response,
                "model": model,
                "provider": provider
            })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass