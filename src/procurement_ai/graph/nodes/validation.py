"""Response validation node."""

import logging

from procurement_ai.config.settings import get_settings
from procurement_ai.guardrails.output_guard import OutputGuard
from procurement_ai.verification.answer_verifier import verify_answer

logger = logging.getLogger(__name__)


def response_validator_node(state: dict) -> dict:
    """Validate response quality, evidence support, and numeric consistency."""
    response = state.get("response", "")
    citations = state.get("citations", [])

    result = OutputGuard.validate(response, citations)

    if result["warnings"]:
        logger.warning(f"Response validation warnings: {result['warnings']}")

    verification = state.get("verification")
    if not verification and get_settings().answer_verification_enabled:
        evidence = [item.get("content", "") for item in state.get("evidence", []) if isinstance(item, dict)]
        verification = verify_answer(
            response,
            evidence,
            citations,
            tool_errors=int(state.get("request_tool_errors") or 0),
        ).to_dict()
        state["verification"] = verification
        if verification.get("status") == "warnings" and state.get("confidence"):
            state["confidence"] = min(float(state["confidence"]), 0.7)

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
