from typing import Dict, List
from app.llm.providers.base_provider import BaseLLM
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.anthropic_provider import AnthropicProvider
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.schemas import LLMConfigModel

class LLMService:
    """Factory service to manage LLM providers"""
    
    _providers = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
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
            
        # Fetch API key from DB for cloud providers if not supplied in kwargs
        if "api_key" not in kwargs and provider_name in ["openai", "anthropic"]:
            db = SessionLocal()
            try:
                record = db.query(LLMConfigModel).filter(LLMConfigModel.provider == provider_name).first()
                if record:
                    kwargs["api_key"] = record.api_key
            except Exception as e:
                print(f"Warning: Failed to fetch API key from DB: {e}")
            finally:
                db.close()
        
        return provider_class(model_name=model_name, **kwargs)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        return list(cls._providers.keys())
    
    @classmethod
    def get_available_models(cls) -> Dict[str, List[str]]:
        """Return available models per provider"""
        return {
            "ollama": ["llama3.2:3b", "llama3.2", "llama3.1", "llama3", "mistral", "gemma2", "phi3"],
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-5-sonnet-latest", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
        }