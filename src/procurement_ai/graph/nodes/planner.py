"""LLM planner node.

Runs before intent classification when PLANNER_MODE=llm. The resulting route is
validated against allow-listed workflows/entities/metrics and stored in state;
the deterministic workflows remain the execution layer.
"""

import logging

from procurement_ai.planner.llm_planner import plan_request

logger = logging.getLogger(__name__)


async def planner_node(state: dict) -> dict:
    question = state.get("user_input", "")
    history = state.get("history", [])

    outcome = await plan_request(question, history)
    decision = outcome.decision

    state["planned_route"] = decision.to_dict() if decision else None
    state["planner_audit"] = {
        "planner_mode": outcome.planner_mode,
        "model": outcome.model,
        "validation_result": outcome.validation_result,
        "fallback_used": outcome.fallback_used,
        "raw_decision": outcome.raw_decision,
        "latency_ms": outcome.latency_ms,
        "input_tokens": outcome.input_tokens,
        "output_tokens": outcome.output_tokens,
    }

    if decision:
        logger.info(
            "LLM planner: workflow=%s intent=%s entity=%s metric=%s",
            decision.workflow,
            decision.intent,
            decision.entity_type,
            decision.metric,
        )
    else:
        logger.info(
            "Planner unavailable or invalid (%s); using deterministic routing",
            outcome.validation_result,
        )
    return state
