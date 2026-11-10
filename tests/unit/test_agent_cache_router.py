"""Tests for agent cache and model routing primitives."""

from procurement_ai.agent.cache import TTLCache
from procurement_ai.agent.model_router import select_agent_model
from procurement_ai.config.settings import get_settings


class TestAgentCache:
    def test_set_get_clear(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", {"value": 1})
        assert cache.get("key") == {"value": 1}
        cache.clear()
        assert cache.get("key") is None

    def test_missing_key(self):
        assert TTLCache(ttl_seconds=60).get("missing") is None


class TestModelRouter:
    def test_meta_request_uses_fast_model(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "agent_fast_model", "fast-model")
        monkeypatch.setattr(settings, "opencode_go_model", "main-model")
        assert select_agent_model("hello", []) == "fast-model"

    def test_tool_question_uses_main_model(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "agent_fast_model", "fast-model")
        monkeypatch.setattr(settings, "opencode_go_model", "main-model")
        assert select_agent_model("show pending approvals", []) == "main-model"

    def test_history_uses_main_model(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "agent_fast_model", "fast-model")
        monkeypatch.setattr(settings, "opencode_go_model", "main-model")
        assert select_agent_model("hello", [{"role": "user", "content": "x"}]) == "main-model"
