import httpx
import json
from .base_provider import BaseLLM
from typing import AsyncGenerator, Dict, Any, Union, List

class AnthropicProvider(BaseLLM):
    """Concrete implementation for Anthropic (Claude) models via direct HTTP completions API"""

    def __init__(self, model_name: str = "claude-3-5-sonnet-latest", api_key: str = None, temperature: float = 0.7, max_tokens: int = 2048):
        super().__init__(model_name, temperature, max_tokens)
        self.api_key = api_key

    def _format_messages(self, prompt: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        
        # Anthropic doesn't allow 'system' role in the messages list.
        # System messages must be passed as a top-level parameter 'system'.
        formatted = []
        for m in prompt:
            # We filter out 'system' messages from the main list (we can capture them if needed)
            if m["role"] == "system":
                continue
            
            # Map 'tool' role to 'user' with a tool response content
            role = m["role"]
            content = m["content"]
            
            if role == "tool":
                # In Anthropic, tool output is sent as a user message with a specific tool_result block
                # However, for simple custom clients, sending a plain text description in a user block is also accepted!
                # E.g. {"role": "user", "content": f"[Tool Output for {m.get('name')}] {content}"}
                role = "user"
                content = f"[Tool Output]: {content}"
                
            formatted.append({
                "role": role,
                "content": content
            })
        return formatted

    def _get_system_message(self, prompt: Union[str, List[Dict[str, Any]]]) -> Union[str, None]:
        if isinstance(prompt, list):
            for m in prompt:
                if m["role"] == "system":
                    return m["content"]
        return None

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-compatible tool definitions to Anthropic's input_schema style"""
        anthropic_tools = []
        if tools:
            for t in tools:
                func = t.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "input_schema": func.get("parameters")
                })
        return anthropic_tools

    async def generate(self, prompt: Union[str, List[Dict[str, Any]]], tools: List[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Generate a complete response from Anthropic, parsing tool_use if invoked"""
        if not self.api_key:
            raise ValueError("Anthropic API key is missing. Please configure it in settings.")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        messages = self._format_messages(prompt)
        anthropic_tools = self._convert_tools(tools)
        system_msg = self._get_system_message(prompt)
        
        payload = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
            **kwargs
        }
        if anthropic_tools:
            payload["tools"] = anthropic_tools
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Anthropic API Error: {response.text}")
            
            data = response.json()
            content_blocks = data.get("content", [])
            
            text_content = ""
            standard_tool_calls = []
            
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content += block.get("text", "")
                elif block.get("type") == "tool_use":
                    standard_tool_calls.append({
                        "id": block.get("id"),
                        "function": {
                            "name": block.get("name"),
                            "arguments": block.get("input", {})
                        }
                    })
                    
            return {
                "content": text_content,
                "tool_calls": standard_tool_calls
            }

    async def stream_generate(self, prompt: Union[str, List[Dict[str, Any]]], tools: List[Dict[str, Any]] = None, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chunks from Anthropic, supporting tokens and tool uses"""
        if not self.api_key:
            raise ValueError("Anthropic API key is missing. Please configure it in settings.")
            
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        messages = self._format_messages(prompt)
        anthropic_tools = self._convert_tools(tools)
        system_msg = self._get_system_message(prompt)
        
        payload = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        if anthropic_tools:
            payload["tools"] = anthropic_tools
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", "https://api.anthropic.com/v1/messages", json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Anthropic API Error: {error_text.decode('utf-8')}")
                
                # Buffer for compiling incoming partial JSON inputs for tools
                current_tool_id = None
                current_tool_name = None
                current_tool_input_str = ""
                
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if not data_str or data_str == "[DONE]":
                            continue
                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get("type")
                            
                            # Case 1: Plain text token
                            if event_type == "content_block_delta" and event_data.get("delta", {}).get("type") == "text_delta":
                                text = event_data.get("delta", {}).get("text", "")
                                if text:
                                    yield {"content": text, "tool_calls": []}
                                    
                            # Case 2: Tool Use Block Starts
                            elif event_type == "content_block_start" and event_data.get("content_block", {}).get("type") == "tool_use":
                                block = event_data.get("content_block", {})
                                current_tool_id = block.get("id")
                                current_tool_name = block.get("name")
                                current_tool_input_str = ""
                                
                            # Case 3: Tool Input Delta
                            elif event_type == "content_block_delta" and event_data.get("delta", {}).get("type") == "input_json_delta":
                                current_tool_input_str += event_data.get("delta", {}).get("partial_json", "")
                                
                            # Case 4: Content Block Ends
                            elif event_type == "content_block_stop":
                                if current_tool_name and current_tool_id:
                                    try:
                                        args = json.loads(current_tool_input_str) if current_tool_input_str else {}
                                    except:
                                        args = current_tool_input_str
                                    
                                    yield {
                                        "content": "",
                                        "tool_calls": [{
                                            "id": current_tool_id,
                                            "function": {
                                                "name": current_tool_name,
                                                "arguments": args
                                            }
                                        }]
                                    }
                                    current_tool_id = None
                                    current_tool_name = None
                                    current_tool_input_str = ""
                        except json.JSONDecodeError:
                            pass

    async def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Anthropic",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "status": "cloud"
        }
