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
    def get_model(self, model_name: str | None = None) -> BaseChatModel:
        """Return the LangChain chat model."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider, preferring OpenCode Go when configured."""

    def __init__(self):
        settings = get_settings()
        self.opencode_key = getattr(settings, "opencode_go_api_key", "")
        self.use_opencode = bool(self.opencode_key)
        if not self.opencode_key and not settings.openai_api_key:
            raise ValueError("OPENCODE_GO_API_KEY or OPENAI_API_KEY is required for the LLM provider")
        self.model_name = (
            getattr(settings, "opencode_go_model", "claude-haiku-5-5") if self.use_opencode else settings.openai_model
        )

    def get_model(self, model_name: str | None = None) -> BaseChatModel:
        settings = get_settings()
        selected_model = model_name or self.model_name
        if self.use_opencode:
            return ChatOpenAI(
                api_key=SecretStr(self.opencode_key),
                model=selected_model,
                temperature=0.1,
                max_completion_tokens=4096,
                base_url=getattr(settings, "opencode_go_base_url", "https://opencode.ai/zen/go/v1"),
                default_headers={
                    "x-opencode-session": getattr(settings, "opencode_session_id", "procurement-ai-planner")
                },
            )

        return ChatOpenAI(
            api_key=SecretStr(settings.openai_api_key),
            model=selected_model,
            temperature=0.1,
            max_completion_tokens=4096,
        )


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model_name = settings.ollama_model

    def get_model(self, model_name: str | None = None) -> BaseChatModel:
        settings = get_settings()
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=model_name or self.model_name,
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


def get_chat_model(model_name: str | None = None) -> BaseChatModel:
    """Get the configured chat model, optionally overriding its model name."""
    provider = get_llm_provider()
    return provider.get_model(model_name=model_name)
