from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional

class BaseLLM(ABC):
    """Abstract Base Class for all LLM providers"""
    
    def __init__(self, model_name: str, temperature: float = 0.7, max_tokens: int = 2048):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a complete response"""
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response token by token (important for WebSocket)"""
        pass

    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Return information about the current model"""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Common config for all providers"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }