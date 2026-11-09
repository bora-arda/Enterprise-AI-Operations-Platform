"""LLM planner node.

Runs before intent classification. The resulting route is validated against
allow-listed workflows/entities/metrics and stored in state. A deterministic
semantic parser acts as a safety net for explicit metric/list questions, and
detail follow-ups reuse the previous metric instead of asking for an invoice.
"""

import logging
import re

from procurement_ai.planner.llm_planner import PlannerDecision, plan_request
from procurement_ai.semantic.parser import parse_metric_request

logger = logging.getLogger(__name__)

DETAIL_FOLLOW_UP = re.compile(
    r"\b(detailed|as a table|table|each of them|all of them|those|them|list them)\b",
    re.IGNORECASE,
)


def _metric_decision(request, reason: str, follow_up: bool = False) -> PlannerDecision:
    return PlannerDecision(
        workflow="sql",
        intent="analyze",
        metric=request.metric,
        dimension=request.dimension,
        days=request.days,
        follow_up=follow_up,
        reason=reason,
    )


async def planner_node(state: dict) -> dict:
    question = state.get("user_input", "")
    history = state.get("history", [])
    previous = state.get("previous_route") or {}

    outcome = await plan_request(question, history, previous_route=previous)
    decision = outcome.decision

    # Safety net: explicit metric/list questions use the governed semantic parser.
    metric_request = parse_metric_request(question)
    if metric_request and (decision is None or decision.workflow != "sql" or decision.metric != metric_request.metric):
        decision = _metric_decision(metric_request, "deterministic semantic metric")
        outcome.validation_result = "corrected"
        outcome.fallback_used = False

    # Detail/table follow-up: reuse the previous metric instead of clarifying.
    if (
        previous.get("metric")
        and DETAIL_FOLLOW_UP.search(question)
        and (decision is None or decision.workflow in ("clarification", "fallback") or decision.follow_up)
    ):
        decision = PlannerDecision(
            workflow="sql",
            intent="analyze",
            metric=previous.get("metric"),
            dimension=previous.get("dimension"),
            days=previous.get("days"),
            follow_up=True,
            reason="detail follow-up on previous metric",
        )
        outcome.validation_result = "accepted"
        outcome.fallback_used = False

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
            "Planner route: workflow=%s intent=%s metric=%s dimension=%s follow_up=%s",
            decision.workflow,
            decision.intent,
            decision.metric,
            decision.dimension,
            decision.follow_up,
        )
    else:
        logger.info(
            "Planner unavailable or invalid (%s); using deterministic routing",
            outcome.validation_result,
        )
    return state
