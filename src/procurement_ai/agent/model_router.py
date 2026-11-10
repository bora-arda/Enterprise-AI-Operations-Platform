"""Lightweight model routing for the agent.

The catalog currently offers one cost-effective default (Claude Haiku 5.5).
The router is deliberately explicit so deployments can configure a fast model
for greetings/help and keep the stronger model for tool-heavy analysis without
changing application code.
"""

import re

from procurement_ai.config.settings import get_settings

META_QUERY = re.compile(
    r"^\s*(hi|hello|hey|greetings|thanks?|thank\s+you|"
    r"help(?:\s+me)?|what\s+can\s+you\s+do|what\s+do\s+you\s+do|"
    r"who\s+are\s+you|what\s+are\s+you|capabilities)\b",
    re.IGNORECASE,
)


def select_agent_model(question: str, history: list[dict] | None = None) -> str:
    settings = get_settings()
    fast_model = (settings.agent_fast_model or "").strip()
    if fast_model and not history and META_QUERY.search(question):
        return fast_model
    return settings.opencode_go_model
