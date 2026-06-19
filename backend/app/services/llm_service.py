from typing import Dict, List
from app.llm.providers.base_provider import BaseLLM
from app.llm.providers.ollama_provider import OllamaProvider
from app.core.config import settings

class LLMService:
    """Factory service to manage LLM providers"""
    
    _providers = {
        "ollama": OllamaProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_name: str = None, model_name: str = None, **kwargs) -> BaseLLM:
        """Return an instance of the requested LLM provider"""
        
        if provider_name is None:
            provider_name = settings.DEFAULT_LLM_PROVIDER
        
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            raise ValueError(f"Provider '{provider_name}' not supported.")
        
        provider_class = cls._providers[provider_name]
        
        if model_name is None:
            model_name = settings.DEFAULT_MODEL_NAME
        
        return provider_class(model_name=model_name, **kwargs)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        return list(cls._providers.keys())
    
    @classmethod
    def get_available_models(cls) -> Dict[str, List[str]]:
        """Return available models per provider"""
        return {
            "ollama": ["llama3.2", "llama3.1", "llama3", "mistral", "gemma2", "phi3"],
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            # Add more when implementing other providers
        }