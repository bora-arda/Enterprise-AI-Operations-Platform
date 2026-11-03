"""Input guardrails node."""

import logging

from procurement_ai.guardrails.input_guard import InputGuard

logger = logging.getLogger(__name__)


def guardrails_node(state: dict) -> dict:
    """Run input validation and safety checks."""
    user_input = state.get("user_input", "")

    result = InputGuard.validate(user_input)

    if not result["valid"]:
        state["response"] = f"Request rejected: {'; '.join(result['errors'])}"
        state["errors"] = result["errors"]
        logger.warning(f"Guardrails rejected input: {result['errors']}")

    return state
