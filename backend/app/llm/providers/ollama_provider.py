from .base_provider import BaseLLM
from typing import AsyncGenerator, Dict, Any
import asyncio

try:
    from langchain_ollama import ChatOllama
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class OllamaProvider(BaseLLM):
    """Concrete implementation for local Ollama models"""
    
    def __init__(self, model_name: str = "llama3.1", temperature: float = 0.7, max_tokens: int = 2048):
        if model_name == "llama3.2":
            model_name = "llama3.2:3b"
        super().__init__(model_name, temperature, max_tokens)
        self._client = None

    async def _get_client(self):
        """Lazy initialization of Ollama client"""
        if self._client is None:
            if not LANGCHAIN_AVAILABLE:
                raise ImportError("langchain-ollama is not installed. Run: pip install langchain-ollama")
            self._client = ChatOllama(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        return self._client

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate complete response"""
        client = await self._get_client()
        response = await client.ainvoke(prompt)
        return response.content

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream tokens one by one"""
        client = await self._get_client()
        async for chunk in client.astream(prompt):
            if chunk.content:
                yield chunk.content

    async def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Ollama",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "status": "local"
        }