"""Clarification node.

When a lookup request is missing an identifier (or an entity is ambiguous),
ask a targeted follow-up instead of guessing.
"""

import logging

logger = logging.getLogger(__name__)


def clarify_node(state: dict) -> dict:
    """Return a clarification prompt."""
    message = state.get("clarification_message") or ("Could you provide more detail so I can find the right record?")
    state["response"] = message
    state["confidence"] = 0.5
    state["workflow"] = "clarification"
    state["intent"] = "clarify"
    logger.info("Clarification requested")
    return state
