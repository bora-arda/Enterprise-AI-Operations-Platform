"""Tests for per-request cost estimation."""

from procurement_ai.config.settings import get_settings
from procurement_ai.observability.cost import RequestUsage, estimate_cost


class TestCost:
    def test_estimate_cost_basic(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_input_cost_per_million", 0.10)
        monkeypatch.setattr(settings, "llm_output_cost_per_million", 0.50)
        monkeypatch.setattr(settings, "llm_cost_context_tier", 100000)
        cost = estimate_cost(10_000, 10_000)
        assert cost == 0.006

    def test_usage_accumulates(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "llm_input_cost_per_million", 0.10)
        monkeypatch.setattr(settings, "llm_output_cost_per_million", 0.50)
        usage = RequestUsage()
        usage.add(1000, 100)
        usage.add(2000, 200)
        assert usage.input_tokens == 3000
        assert usage.output_tokens == 300
        assert usage.llm_calls == 2
        assert usage.cost_usd > 0
