import httpx
import json
from typing import Dict, Any

class ToolExecutor:
    """Service to execute built-in and dynamic API tools"""

    @classmethod
    def is_valid_tool_call(cls, tc: Dict[str, Any], valid_tool_names: set) -> bool:
        """Validate if a tool call format from LLM is correct and exists in registry"""
        if not isinstance(tc, dict):
            return False
        func = tc.get("function")
        if not func or not isinstance(func, dict):
            return False
        name = func.get("name")
        if not name or not isinstance(name, str):
            return False
        if name not in valid_tool_names:
            return False
        
        args = func.get("arguments")
        if args is None:
            return False
        if isinstance(args, str):
            try:
                json.loads(args)
            except Exception:
                return False
        elif not isinstance(args, dict):
            return False
            
        return True

    @classmethod
    def should_provide_tools(cls, message: str) -> bool:
        """Determine if we should pass tools to the LLM based on the user's message"""
        if not message:
            return False
        msg_lower = message.lower().strip()
        
        # 1. Explicit tool denial keywords
        no_tools_phrases = [
            "dont use", "don't use", "do not use", "no tools", "without tools",
            "without using", "dont call", "don't call", "do not call"
        ]
        if any(phrase in msg_lower for phrase in no_tools_phrases):
            return False
            
        # 2. Greetings and simple chat checks
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "how are you", "who are you"]
        if msg_lower in greetings:
            return False
        for g in greetings:
            if msg_lower.startswith(g) and len(msg_lower) < 20:
                return False
                
        # 3. Jokes / conversational asks
        chat_phrases = [
            "tell me a joke", "tell a joke", "make me laugh", "say a joke", 
            "sing a song", "write a poem", "tell me a story", "say something funny"
        ]
        if any(phrase in msg_lower for phrase in chat_phrases):
            return False
            
        return True



    @classmethod
    async def execute(cls, name: str, parameters: Dict[str, Any]) -> str:
        """Find the tool configuration and execute it"""
        
        # 1. Check if it is a built-in tool
        if name == "calculator":
            return cls._execute_calculator(parameters.get("expression", ""))
        elif name == "search_web":
            return cls._execute_search_web(parameters.get("query", ""))
        elif name == "rag_lookup":
            return await cls._execute_rag_lookup(parameters.get("query", ""))

        # 2. Check the PostgreSQL database for custom dynamic API tools
        from app.core.db import SessionLocal
        from app.models.schemas import ToolModel
        
        db = SessionLocal()
        try:
            tool = db.query(ToolModel).filter(ToolModel.name == name).first()
            if not tool:
                return f"Error: Tool '{name}' not found in registry."
            
            if tool.type == "api" and tool.url:
                return await cls._execute_api_tool(
                    url=tool.url,
                    method=tool.method or "GET",
                    parameters=parameters,
                    headers=tool.headers
                )
            else:
                return f"Error: Tool '{name}' has type '{tool.type}' but lacks configuration to run."
        except Exception as e:
            return f"Error executing registry tool: {str(e)}"
        finally:
            db.close()

    @classmethod
    def _execute_calculator(cls, expression: str) -> str:
        """Safely evaluate mathematical expressions"""
        if not expression:
            return "Error: Empty expression"
        
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters. Only numbers and basic operators (+,-,*,/,parentheses) allowed."
        
        try:
            # Safe local environment
            result = eval(expression, {"__builtins__": None}, {})
            return f"Calculation Result: {expression} = {result}"
        except Exception as e:
            return f"Calculation Error: {str(e)}"

    @classmethod
    def _execute_search_web(cls, query: str) -> str:
        """Mock internet search results"""
        if not query:
            return "Error: Empty query"
        return (
            f"Web search results for '{query}':\n"
        )

    @classmethod
    async def _execute_rag_lookup(cls, query: str) -> str:
        """Retrieve relevant context chunks from the vector database (Qdrant)"""
        if not query:
            return "Error: Empty query"
            
        try:
            from app.services.vector_store import query_vector_store
            chunks = await query_vector_store(query, top_k=3)
            if not chunks:
                return f"No matching documents found in knowledge base for query: '{query}'"
            
            context_list = []
            for idx, c in enumerate(chunks, 1):
                metadata = c.get("metadata", {})
                filename = metadata.get("filename", "Unknown file")
                score = c.get("score", 0.0)
                context_list.append(f"[{idx}] Source: {filename} (score: {score:.2f})\nContent: {c['text']}")
            
            return "Relevant knowledge base context:\n\n" + "\n\n---\n\n".join(context_list)
        except Exception as e:
            return f"Error retrieving knowledge context: {str(e)}"

    @classmethod
    async def _execute_api_tool(cls, url: str, method: str, parameters: Dict[str, Any], headers: Dict[str, Any] = None) -> str:
        """Execute external API HTTP endpoints dynamically"""
        headers = headers or {}
        method = method.upper()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, params=parameters, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=parameters, headers=headers)
                else:
                    return f"Error: Unsupported HTTP method '{method}'"
                
                return f"API Tool Response (Status {response.status_code}):\n{response.text}"
        except Exception as e:
            return f"API Connection Error: {str(e)}"
