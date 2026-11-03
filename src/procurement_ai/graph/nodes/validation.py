"""Response validation node."""

import logging

from procurement_ai.guardrails.output_guard import OutputGuard

logger = logging.getLogger(__name__)


def response_validator_node(state: dict) -> dict:
    """Validate response quality and evidence support."""
    response = state.get("response", "")
    citations = state.get("citations", [])

    result = OutputGuard.validate(response, citations)

    if result["warnings"]:
        logger.warning(f"Response validation warnings: {result['warnings']}")

    # Preserve workflow-provided confidence; only default when missing.
    if result["hallucination_indicators"]:
        state["errors"] = state.get("errors", []) + ["Potential hallucination detected"]
        state["confidence"] = 0.3
    elif state.get("confidence") is None:
        state["confidence"] = 0.8 if citations else 0.4

    # Append the assistant turn to conversation memory (kept to 10 messages).
    history = list(state.get("history", []))
    history.append({"role": "assistant", "content": state.get("response", "")})
    state["history"] = history[-10:]

    return state
