"""Unit tests for LLM and embedding provider abstractions."""

import pytest

from procurement_ai.models.embeddings import EmbeddingProvider, get_embedding_provider
from procurement_ai.models.llm import LLMProvider, OpenAIProvider, get_llm_provider


class _FakeSettings:
    def __init__(self, provider: str):
        self.llm_provider = provider
        self.embedding_provider = provider
        self.openai_api_key = "test-key"
        self.openai_model = "gpt-4o-mini"
        self.ollama_base_url = "http://localhost:11434"
        self.ollama_model = "llama3.1"
        self.embedding_model = "text-embedding-3-small"


class TestLLMProvider:
    def test_openai_provider(self, monkeypatch):
        from procurement_ai.models import llm

        monkeypatch.setattr(llm, "get_settings", lambda: _FakeSettings("openai"))
        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)
        assert isinstance(provider, LLMProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        from procurement_ai.models import llm

        monkeypatch.setattr(llm, "get_settings", lambda: _FakeSettings("invalid"))
        with pytest.raises(ValueError):
            get_llm_provider()


class TestEmbeddingProvider:
    def test_provider_factory(self, monkeypatch):
        from procurement_ai.models import embeddings

        monkeypatch.setattr(embeddings, "get_settings", lambda: _FakeSettings("openai"))
        provider = get_embedding_provider()
        assert isinstance(provider, EmbeddingProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        from procurement_ai.models import embeddings

        monkeypatch.setattr(embeddings, "get_settings", lambda: _FakeSettings("invalid"))
        with pytest.raises(ValueError):
            get_embedding_provider()
