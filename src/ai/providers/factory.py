"""Provider factory to get the correct LLM and embedding providers."""

from src.core.config import get_settings
from src.ai.providers.base import BaseLLMProvider
from src.ai.providers.openai_compatible import OpenAICompatibleProvider
from src.ai.providers.embeddings.base import BaseEmbeddingProvider
from src.ai.providers.embeddings.openai_compatible import OpenAICompatibleEmbeddingProvider

def get_llm_provider() -> BaseLLMProvider:
    """Get the configured LLM provider."""
    settings = get_settings()
    
    if settings.llm_provider == "lmstudio":
        return OpenAICompatibleProvider(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",
            model_name=settings.lmstudio_llm_model,
            provider_name="lmstudio",
            default_temperature=settings.llm_temperature,
            default_max_tokens=settings.llm_max_tokens,
        )
    else:
        return OpenAICompatibleProvider(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.google_api_key,
            model_name=settings.google_llm_model,
            provider_name="google",
            default_temperature=settings.llm_temperature,
            default_max_tokens=settings.llm_max_tokens,
        )

def get_embedding_provider() -> BaseEmbeddingProvider:
    """Get the configured embedding provider."""
    settings = get_settings()
    
    if settings.embed_provider == "lmstudio":
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",
            model_name=settings.lmstudio_embed_model,
            dimensions=settings.embed_dimensions
        )
    else:
        return OpenAICompatibleEmbeddingProvider(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.google_api_key,
            model_name=settings.google_embed_model,
            dimensions=settings.embed_dimensions
        )
