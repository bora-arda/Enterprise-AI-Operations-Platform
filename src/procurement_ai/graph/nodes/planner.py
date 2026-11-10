"""LLM planner node.

Runs before intent classification. The resulting route is validated against
allow-listed workflows/entities/metrics and stored in state. A deterministic
semantic parser acts as a safety net for explicit metric/list questions, and
detail follow-ups reuse the previous metric instead of asking for an invoice.
"""

import logging
import re

from procurement_ai.config.settings import get_settings
from procurement_ai.graph.nodes.intent import classify_intent
from procurement_ai.planner.llm_planner import PlannerDecision, plan_request
from procurement_ai.security.access import scope_from_state
from procurement_ai.semantic.parser import parse_metric_request

logger = logging.getLogger(__name__)

DETAIL_FOLLOW_UP = re.compile(
    r"\b(detailed|as a table|table|each of them|all of them|those|them|list them)\b",
    re.IGNORECASE,
)

META_HELP = re.compile(
    r"^\s*(?:(?:could|can|would)\s+you\s+)?("
    r"hi|hello|hey|greetings|thanks?|thank\s+you|"
    r"good\s+(morning|afternoon|evening)|"
    r"help(?:\s+me)?|i\s+need\s+help|what\s+can\s+you\s+do|"
    r"what\s+do\s+you\s+do|tell\s+me\s+what\s+you\s+can\s+do|"
    r"what\s+are\s+your\s+capabilities|how\s+can\s+you\s+help|"
    r"who\s+are\s+you|what\s+are\s+you|capabilities)\b",
    re.IGNORECASE,
)

PENDING_ALL = re.compile(
    r"^\s*(all(?:\s+of\s+them|\s+three|\s+please)?|everything|both|the\s+lot|show\s+all)"
    r"\s*[.!?]*$|\bi\s+(?:just\s+)?said\s+all\b",
    re.IGNORECASE,
)

PENDING_FRAGMENT = re.compile(r"^\s*pend(?:ing)?\s*[.!?]*$", re.IGNORECASE)

POLICY_QUERY = re.compile(
    r"\b(policy|policies|procedure|procedures|process|guidance|rules?|requirements?)\b",
    re.IGNORECASE,
)

EXCEPTION_DETAIL = re.compile(
    r"\b(invoice\s+(?:exceeds?|over)\s+(?:its\s+)?(?:po|purchase\s+order)|"
    r"(?:exceeds?|over)\s+(?:the\s+)?po|missing\s+approvals?|already\s+paid|"
    r"duplicate\s+invoices?|payment\s+mismatch|wrong\s+vendor|wrong\s+currency|"
    r"expired\s+contracts?|invalid\s+po)\b",
    re.IGNORECASE,
)

DETECTION_REQUEST = re.compile(
    r"\b(find|detect|scan|look\s+for)\b.*\b(duplicates?|anomal|issues?|problems?)\b",
    re.IGNORECASE,
)

COMPLEX_QUERY = re.compile(
    r"\b(compare|comparing|versus|vs\.?|excluding|except|join|group\s+by|"
    r"quarter|q[1-4]|year\s+over\s+year|yoy|breakdown|top(?:\s+\d+)?|"
    r"highest|lowest|most|change[sd]?|increas(?:e|ed|ing)|decreas(?:e|ed|ing)|"
    r"grew|grow(?:th)?|trend|declin(?:e|ed|ing)|difference|delta|rank(?:ing)?)\b"
    r"|\bfrom\b.+\bto\b",
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


def _agent_decision(reason: str) -> PlannerDecision:
    return PlannerDecision(
        workflow="agent",
        intent="analyze",
        follow_up=False,
        reason=reason,
    )


def _pending_categories(text: str) -> set[str]:
    """Return pending categories mentioned, keeping payment requests separate."""
    q = text.lower()
    if not re.search(r"\bpending\b", q):
        return set()

    categories: set[str] = set()
    if re.search(r"\bapprovals?\b", q):
        categories.add("approvals")
    if re.search(r"\bpayment\s+requests?\b", q):
        categories.add("payment_requests")
        q = re.sub(r"\bpayment\s+requests?\b", "", q)
    if re.search(r"\bpayments?\b", q):
        categories.add("payments")
    return categories


def _has_pending_clarification(previous: dict, history: list[dict]) -> bool:
    """Detect an earlier clarification that offered multiple pending categories."""
    texts = [str(previous.get("clarification_message") or "")]
    for message in history[-8:]:
        texts.append(str(message.get("content") or ""))
    blob = " ".join(texts).lower()
    categories = sum(
        term in blob
        for term in (
            "pending approvals",
            "pending payment requests",
            "pending payments",
        )
    )
    return categories >= 2


async def planner_node(state: dict) -> dict:
    question = state.get("user_input", "")
    history = state.get("history", [])
    previous = state.get("previous_route") or {}
    settings = get_settings()
    scope = scope_from_state(state)
    restricted = settings.row_level_access_enabled and scope.restricted
    action_requested = classify_intent(question) == "act"
    decision: PlannerDecision | None

    # Agent-first mode: use the tool-calling agent for all read-only questions.
    # Controls such as payment/approval actions remain on the deterministic,
    # human-in-the-loop action workflow. Hybrid mode retains planner routing.
    # Restricted users are forced through the scoped agent for read-only work.
    if action_requested and restricted:
        decision = PlannerDecision(
            workflow="action",
            intent="act",
            follow_up=False,
            reason="restricted-user controlled action",
        )
        state["planned_route"] = decision.to_dict()
        state["planner_audit"] = {
            "planner_mode": "agent_first",
            "model": None,
            "validation_result": "accepted",
            "fallback_used": False,
            "raw_decision": None,
            "latency_ms": 0,
            "input_tokens": None,
            "output_tokens": None,
        }
        return state

    if restricted and not settings.opencode_go_api_key:
        decision = PlannerDecision(
            workflow="fallback",
            intent="out_of_scope",
            follow_up=False,
            reason="restricted user requires scoped agent; LLM unavailable",
        )
        state["planned_route"] = decision.to_dict()
        state["planner_audit"] = {
            "planner_mode": "agent_first",
            "model": None,
            "validation_result": "accepted",
            "fallback_used": True,
            "raw_decision": None,
            "latency_ms": 0,
            "input_tokens": None,
            "output_tokens": None,
        }
        return state

    if (settings.orchestration_mode.lower() == "agent_first" and settings.opencode_go_api_key) or (
        restricted and settings.opencode_go_api_key
    ):
        agent_first_decision = PlannerDecision(
            workflow="action" if action_requested else "agent",
            intent="act" if action_requested else "analyze",
            follow_up=False,
            reason=(
                "agent-first controlled action"
                if action_requested
                else "agent-first: model-directed read-only analysis"
            ),
        )
        state["planned_route"] = agent_first_decision.to_dict()
        state["planner_audit"] = {
            "planner_mode": "agent_first",
            "model": None,
            "validation_result": "accepted",
            "fallback_used": False,
            "raw_decision": None,
            "latency_ms": 0,
            "input_tokens": None,
            "output_tokens": None,
        }
        logger.info(
            "Agent-first route: workflow=%s intent=%s",
            agent_first_decision.workflow,
            agent_first_decision.intent,
        )
        return state

    outcome = await plan_request(question, history, previous_route=previous)
    decision = outcome.decision

    # Open-ended/comparative questions go to the tool-calling agent.
    is_complex = bool(COMPLEX_QUERY.search(question))
    if is_complex and (decision is None or decision.workflow in ("sql", "retrieval", "fallback")):
        decision = PlannerDecision(
            workflow="agent",
            intent="analyze",
            follow_up=False,
            reason="open-ended analytical question",
        )
        outcome.validation_result = "corrected"
        outcome.fallback_used = False

    # Safety net: explicit simple metric/list questions use the governed parser.
    metric_request = parse_metric_request(question)
    if (
        not is_complex
        and metric_request
        and (decision is None or decision.workflow != "sql" or decision.metric != metric_request.metric)
    ):
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

    # Multi-category pending questions, and "all" after a pending-category
    # clarification, need more than one governed metric. Let the agent choose
    # the relevant metrics/tools and combine the answer.
    multi_pending = len(_pending_categories(question)) >= 2
    pending_all_followup = bool(PENDING_ALL.search(question)) and _has_pending_clarification(previous, history)
    if (multi_pending or pending_all_followup) and (
        decision is None or decision.workflow in ("sql", "retrieval", "fallback", "clarification")
    ):
        decision = _agent_decision("multi-category pending overview")
        outcome.validation_result = "corrected"
        outcome.fallback_used = False

    # Policy/procedure questions are document questions. The retrieval workflow
    # returns the best excerpt; the agent can search multiple documents and
    # synthesize a more useful answer with citations.
    if POLICY_QUERY.search(question) and decision and decision.workflow in ("sql", "retrieval"):
        decision = _agent_decision("policy question requiring document synthesis")
        outcome.validation_result = "corrected"
        outcome.fallback_used = False

    # Detection follow-ups name an exception category ("invoice exceeds po",
    # "missing approvals", ...). These need live invoice/PO detail and often
    # several lookups, so route them to the agent rather than clarification or
    # a single-rule response.
    exception_detail = bool(EXCEPTION_DETAIL.search(question))
    previous_detection = previous.get("workflow") == "detection"
    if (
        exception_detail
        and not DETECTION_REQUEST.search(question)
        and (decision is None or decision.workflow in ("sql", "retrieval", "fallback", "clarification", "detection"))
    ):
        decision = _agent_decision("exception detail request")
        outcome.validation_result = "corrected"
        outcome.fallback_used = False
    elif previous_detection and DETAIL_FOLLOW_UP.search(question) and not exception_detail:
        decision = _agent_decision("detailed follow-up on detected exceptions")
        outcome.validation_result = "corrected"
        outcome.fallback_used = False

    # Greetings/help questions should get a natural response, and explicit
    # planner fallbacks go to the agent (its prompt declines truly unrelated
    # requests). If the planner is unavailable (decision is None), leave the
    # deterministic router in place so entity lookups still work.
    if decision is None and (
        META_HELP.search(question)
        or PENDING_FRAGMENT.search(question)
        or POLICY_QUERY.search(question)
        or classify_intent(question) == "out_of_scope"
    ):
        decision = _agent_decision("ambiguous/conversational request")
        outcome.validation_result = "corrected"
        outcome.fallback_used = False
    elif decision is not None and (
        decision.workflow == "fallback"
        or (decision.workflow in ("clarification", "retrieval") and META_HELP.search(question))
    ):
        decision = _agent_decision("conversational/help fallback")
        outcome.validation_result = "corrected"
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
