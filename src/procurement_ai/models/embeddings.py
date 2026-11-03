"""Embedding provider abstraction."""

import logging
from abc import ABC, abstractmethod

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from sentence_transformers import SentenceTransformer

from procurement_ai.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def get_embeddings(self) -> Embeddings:
        """Return the LangChain embeddings model."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        self.model_name = settings.embedding_model

    def get_embeddings(self) -> Embeddings:
        settings = get_settings()
        return OpenAIEmbeddings(
            api_key=SecretStr(settings.openai_api_key),
            model=self.model_name,
        )


_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def _get_sentence_transformer(model_name: str) -> SentenceTransformer:
    """Load and cache a sentence-transformers model process-wide."""
    if model_name not in _MODEL_CACHE:
        logger.info(f"Loading embedding model {model_name}")
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local sentence-transformers embedding provider."""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.embedding_model or "all-MiniLM-L6-v2"

    def get_embeddings(self) -> Embeddings:
        class _Wrapper(Embeddings):
            def __init__(self, model_name: str):
                self.model_name = model_name

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                model = _get_sentence_transformer(self.model_name)
                return model.encode(texts).tolist()

            def embed_query(self, text: str) -> list[float]:
                model = _get_sentence_transformer(self.model_name)
                return model.encode([text])[0].tolist()

        return _Wrapper(self.model_name)


def get_embedding_provider() -> EmbeddingProvider:
    """Get the configured embedding provider."""
    settings = get_settings()
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider()
    elif settings.embedding_provider == "sentence_transformers":
        return SentenceTransformerEmbeddingProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


def get_embeddings() -> Embeddings:
    """Get the configured embeddings model."""
    provider = get_embedding_provider()
    return provider.get_embeddings()
