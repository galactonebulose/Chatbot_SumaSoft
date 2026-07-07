import os
import sys
import json
import asyncio

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService
from app.services.executor import ToolExecutor
from app.api.chat import get_db_tools
from app.core.db import SessionLocal

async def test_full_loop():
    # Load LLM
    llm = LLMService.get_provider(provider_name="ollama", model_name="llama3.2:3b")
    
    # Load tools
    db = SessionLocal()
    try:
        tools_list = get_db_tools(db)
    finally:
        db.close()
        
    print(f"Loaded tools count: {len(tools_list)}")
    print("Tools:")
    print(json.dumps(tools_list, indent=2))
    
    # Query
    message = "What is 3 + 9 / 2?"
    print(f"\nUser query: '{message}'")
    
    system_prompt = (
        "You are a helpful assistant. You have access to tools: 'calculator' (for basic arithmetic), "
        "'search_web' (for web queries), and 'rag_lookup' (for searching the local document knowledge base). "
        "Only call tools when appropriate. If no tool is needed, respond directly."
    )
    
    history = [{"role": "user", "content": message}]
    executed_calls = []
    
    loop_limit = 5
    for iteration in range(loop_limit):
        llm_messages = [{"role": "system", "content": system_prompt}] + history
        print(f"\n--- ITERATION {iteration} ---")
        print("Messages sent to LLM:")
        print(json.dumps(llm_messages, indent=2))
        
        response_data = await llm.generate(llm_messages, tools=tools_list)
        print("Ollama Raw Response:")
        print(json.dumps(response_data, indent=2))
        
        content = response_data.get("content", "")
        tool_calls = response_data.get("tool_calls", [])
        
        if not tool_calls:
            print(f"\nFinal response: {content}")
            break
            
        assistant_msg = {
            "role": "assistant",
            "content": content or None,
            "tool_calls": []
        }
        
        tool_results_to_log = []
        for tc in tool_calls:
            call_id = tc.get("id") or "call_mocked"
            func_name = tc["function"]["name"]
            func_args = tc["function"]["arguments"]
            
            # Support parsing stringified arguments
            if isinstance(func_args, str):
                try:
                    func_args = json.loads(func_args)
                except Exception:
                    pass
            
            assistant_msg["tool_calls"].append({
                "id": call_id,
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(func_args)
                }
            })
            
            print(f"Executing: {func_name} with {func_args}")
            result_text = await ToolExecutor.execute(func_name, func_args)
            print(f"Result: {result_text}")
            
            tool_msg = {
                "role": "tool",
                "tool_call_id": call_id,
                "name": func_name,
                "content": result_text
            }
            tool_results_to_log.append(tool_msg)
            
        history.append(assistant_msg)
        for tr in tool_results_to_log:
            history.append(tr)
            
    else:
        print("\nFailed to terminate within loop limit.")

if __name__ == "__main__":
    asyncio.run(test_full_loop())
