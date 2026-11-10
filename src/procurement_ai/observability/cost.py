"""LLM usage and cost helpers.

Pricing defaults reflect the configured OpenCode Go Claude Haiku 5.5 catalog at
the time this integration was built. Prices are configurable so deployment
owners can override them without code changes.
"""

from dataclasses import dataclass

from procurement_ai.config.settings import get_settings


def estimate_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    cache_read_tokens: int | None = None,
    cache_write_tokens: int | None = None,
) -> float:
    settings = get_settings()
    input_tokens = max(int(input_tokens or 0), 0)
    output_tokens = max(int(output_tokens or 0), 0)
    cache_read_tokens = max(int(cache_read_tokens or 0), 0)
    cache_write_tokens = max(int(cache_write_tokens or 0), 0)

    if input_tokens >= settings.llm_cost_context_tier:
        input_rate = settings.llm_input_cost_per_million_high
        output_rate = settings.llm_output_cost_per_million_high
        cache_rate = settings.llm_cache_read_cost_per_million * 5
    else:
        input_rate = settings.llm_input_cost_per_million
        output_rate = settings.llm_output_cost_per_million
        cache_rate = settings.llm_cache_read_cost_per_million

    return (
        input_tokens * input_rate
        + output_tokens * output_rate
        + cache_read_tokens * cache_rate
        + cache_write_tokens * input_rate
    ) / 1_000_000


@dataclass
class RequestUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    llm_calls: int = 0

    def add(
        self,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        *,
        cache_read_tokens: int | None = None,
        cache_write_tokens: int | None = None,
    ) -> float:
        cost = estimate_cost(
            input_tokens,
            output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
        )
        self.input_tokens += max(int(input_tokens or 0), 0)
        self.output_tokens += max(int(output_tokens or 0), 0)
        self.cache_read_tokens += max(int(cache_read_tokens or 0), 0)
        self.cache_write_tokens += max(int(cache_write_tokens or 0), 0)
        self.cost_usd += cost
        self.llm_calls += 1
        return cost

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "cost_usd": round(self.cost_usd, 8),
            "llm_calls": self.llm_calls,
        }
