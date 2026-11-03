"""LLM provider abstraction."""

import logging
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from procurement_ai.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """Return the LangChain chat model."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        self.model_name = settings.openai_model

    def get_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatOpenAI(
            api_key=SecretStr(settings.openai_api_key),
            model=self.model_name,
            temperature=0.1,
            max_completion_tokens=4096,
        )


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model_name = settings.ollama_model

    def get_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=self.model_name,
            temperature=0.1,
        )


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider."""
    settings = get_settings()
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    elif settings.llm_provider == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_chat_model() -> BaseChatModel:
    """Get the configured chat model."""
    provider = get_llm_provider()
    return provider.get_model()
