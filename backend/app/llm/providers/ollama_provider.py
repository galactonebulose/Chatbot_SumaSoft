import httpx
import json
from .base_provider import BaseLLM
from typing import AsyncGenerator, Dict, Any, Union, List

class OllamaProvider(BaseLLM):
    """Concrete implementation for local Ollama models calling /api/chat directly"""
    
    def __init__(self, model_name: str = "llama3.1", temperature: float = 0.7, max_tokens: int = 2048):
        if model_name == "llama3.2":
            model_name = "llama3.2:3b"
        super().__init__(model_name, temperature, max_tokens)
        self.base_url = "http://localhost:11434"

    def _format_messages(self, prompt: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
            
        import copy
        formatted = []
        for msg in prompt:
            msg_copy = copy.deepcopy(msg)
            if "tool_calls" in msg_copy and msg_copy["tool_calls"]:
                for tc in msg_copy["tool_calls"]:
                    func = tc.get("function", {})
                    if "arguments" in func:
                        args = func["arguments"]
                        if isinstance(args, str):
                            try:
                                func["arguments"] = json.loads(args)
                            except Exception:
                                try:
                                    import ast
                                    func["arguments"] = ast.literal_eval(args)
                                except Exception as e:
                                    print(f"Ollama formatting warning: Failed to parse arguments string {args}: {e}")
            if msg_copy.get("role") == "tool":
                if "name" in msg_copy and "tool_name" not in msg_copy:
                    msg_copy["tool_name"] = msg_copy["name"]
            formatted.append(msg_copy)
        return formatted

    async def generate(self, prompt: Union[str, List[Dict[str, Any]]], tools: List[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Generate response (can return text or tool call objects)"""
        messages = self._format_messages(prompt)
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            if response.status_code != 200:
                raise Exception(f"Ollama API Error: {response.text}")
            
            data = response.json()
            message = data.get("message", {})
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }

    async def stream_generate(self, prompt: Union[str, List[Dict[str, Any]]], tools: List[Dict[str, Any]] = None, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chunks from Ollama (can stream tokens or tool calls)"""
        messages = self._format_messages(prompt)
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Ollama API Error: {error_text.decode('utf-8')}")
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        message = chunk.get("message", {})
                        content = message.get("content", "")
                        tool_calls = message.get("tool_calls", [])
                        
                        if content or tool_calls:
                            yield {
                                "content": content,
                                "tool_calls": tool_calls
                            }
                    except json.JSONDecodeError:
                        pass

    async def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Ollama",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "status": "local"
        }