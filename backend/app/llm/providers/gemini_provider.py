from .base_provider import BaseLLM
from typing import AsyncGenerator, Dict, Any, Union, List
from openai import AsyncOpenAI
import json

class GeminiProvider(BaseLLM):
    """Concrete implementation for Google Gemini models via OpenAI-compatible endpoint"""
    
    def __init__(self, model_name: str = "gemini-3.5-flash", api_key: str = None, temperature: float = 0.7, max_tokens: int = 2048):
        super().__init__(model_name, temperature, max_tokens)
        self.api_key = api_key
        self._client = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self.api_key:
                raise ValueError("Gemini API key is missing. Please configure it in settings/database.")
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        return self._client

    def _format_messages(self, prompt: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        return prompt

    async def generate(self, prompt: Union[str, List[Dict[str, Any]]], tools: List[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Generate response and standardize tool calls if triggered"""
        client = self._get_client()
        messages = self._format_messages(prompt)
        
        call_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **kwargs
        }
        if tools:
            call_params["tools"] = tools

        response = await client.chat.completions.create(**call_params)
        msg_obj = response.choices[0].message
        
        standard_tool_calls = []
        if msg_obj.tool_calls:
            for tc in msg_obj.tool_calls:
                args = {}
                try:
                    args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                except Exception:
                    pass
                tc_dict = {
                    "id": tc.id,
                    "type": tc.type or "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args
                    }
                }
                if tc.model_extra:
                    tc_dict.update(tc.model_extra)
                standard_tool_calls.append(tc_dict)

        return {
            "content": msg_obj.content or "",
            "tool_calls": standard_tool_calls
        }

    async def stream_generate(self, prompt: Union[str, List[Dict[str, Any]]], tools: List[Dict[str, Any]] = None, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chunks, supporting tokens and tool calls standard format"""
        client = self._get_client()
        messages = self._format_messages(prompt)
        
        call_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
            **kwargs
        }
        if tools:
            call_params["tools"] = tools

        stream = await client.chat.completions.create(**call_params)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content or ""
            
            standard_tool_calls = []
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    tc_dict = {
                        "id": tc.id,
                        "index": tc.index,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or ""
                        }
                    }
                    if tc.model_extra:
                        tc_dict.update(tc.model_extra)
                    standard_tool_calls.append(tc_dict)
            
            if content or standard_tool_calls:
                yield {
                    "content": content,
                    "tool_calls": standard_tool_calls
                }

    async def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Gemini",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "status": "cloud"
        }
