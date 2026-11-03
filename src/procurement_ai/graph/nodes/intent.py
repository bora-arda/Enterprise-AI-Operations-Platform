"""Intent classification and routing node.

Uses deterministic keyword rules (fast, predictable, no LLM dependency).
LLM-based classification can be layered on later for ambiguous inputs.
"""

import logging
import re

from procurement_ai.graph.nodes.entities import (
    clarification_message,
    has_entity_id,
)

logger = logging.getLogger(__name__)

# Ordered rules: first match wins
INTENT_RULES: list[tuple[str, list[str]]] = [
    # Actions (check before investigation/detection)
    (
        "act",
        [
            r"\brequest\s+payment\b",
            r"\bpay\s+(invoice|inv-)",
            r"\bapprove\b",
            r"\bcreate\s+(an?\s+)?(exception|request|approval)",
            r"\braise\s+(an?\s+)?(exception|request)",
            r"\bsubmit\s+payment\b",
        ],
    ),
    # Detection
    (
        "detect",
        [
            r"\bdetect\b",
            r"\banomal",
            r"\bduplicate",
            r"\bviolat",
            r"\bfraud",
            r"\bmissing\s+approval",
            r"\bfind\s+(transactions|issues|problems)",
        ],
    ),
    # Investigation (multi-step, evidence gathering)
    (
        "investigate",
        [
            r"\bwhy\b",
            r"\binvestigate\b",
            r"\bcomply\b",
            r"\bcompliance\b",
            r"\bmatch(es)?\b",
            r"\bexplain\b",
            r"\bdiscrepanc",
            r"\boverdue\b.*\bwhy\b",
        ],
    ),
    # Analytics / SQL
    (
        "analyze",
        [
            r"\bspending\b",
            r"\btop\s+(vendors|categories|suppliers)",
            r"\baverage\s+invoice",
            r"\bhow\s+many\b",
            r"\bpercentage\b",
            r"\brate\b",
            r"\bcycle\s+time\b",
            r"\baverage\s+approval\b",
            r"\bexpire|expiring|expiration\b",
            r"\bby\s+month\b",
            r"\bby\s+category\b",
            r"\bby\s+department\b",
            r"\btrend",
            r"\bwhich\s+vendors?\b.*\b(exceptions|issues)\b",
            r"\bmost\s+exceptions\b",
        ],
    ),
    # Data queries
    (
        "query",
        [
            r"\bwhich\s+invoices?\b",
            r"\blist\b",
            r"\bshow\s+me\b.*\b(invoices?|purchase orders?|contracts?|payments?)\b",
            r"\boverdue\s+invoices?\b",
            r"\bexpire\b",
            r"\boutstanding\b",
        ],
    ),
    # Simple lookups
    (
        "find",
        [
            r"\bstatus\b",
            r"\bdetails?\b",
            r"\bwhat\s+is\b",
            r"\bwhat\s+are\b",
            r"\bpayment\s+terms\b",
            r"\bprocess\s+for\b",
        ],
    ),
]

# Domain guard: if no procurement term is present and no rule matches, out of scope
PROCUREMENT_TERMS = [
    "invoice",
    "inv-",
    "purchase order",
    "po-",
    "contract",
    "vendor",
    "supplier",
    "payment",
    "procurement",
    "approval",
    "budget",
    "spend",
    "tender",
    "compliance",
    "policy",
    "purchas",
    "pay",
    "requisition",
    "order",
    "procure",
]


def classify_intent(text: str) -> str:
    """Classify intent using a domain guard plus ordered keyword rules."""
    text_lower = text.lower().strip()

    # Domain guard first: reject clearly unrelated questions
    if not any(term in text_lower for term in PROCUREMENT_TERMS):
        return "out_of_scope"

    # Entity lookups (INV-, PO-, CF-, PAY-, APPR-) are single-record retrieval.
    # Invoice compliance questions remain multi-step investigations.
    if has_entity_id(text_lower):
        if re.search(r"\binv-\d+\b", text_lower) and re.search(
            r"\b(why|comply|match|explain|discrepanc|investigate)\b", text_lower
        ):
            return "investigate"
        return "find"

    for intent, patterns in INTENT_RULES:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return intent

    return "find"


INTENT_TO_WORKFLOW = {
    "find": "retrieval",
    "understand": "retrieval",
    "query": "sql",
    "analyze": "sql",
    "investigate": "investigation",
    "detect": "detection",
    "act": "action",
    "clarify": "clarification",
    "out_of_scope": "fallback",
}


FOLLOW_UP_RE = re.compile(
    r"\b(it|its|that|this|the same|previous)\b|\bwhat about\b|\band the\b",
    re.IGNORECASE,
)


def intent_classifier_node(state: dict) -> dict:
    """Apply the LLM planner route, or fall back to deterministic classification."""
    question = state.get("user_input", "")
    state["clarification_needed"] = False
    state["clarification_message"] = ""

    planned = state.get("planned_route") or {}
    if planned.get("workflow"):
        workflow = planned["workflow"]
        intent = planned.get("intent") or "find"

        if workflow == "clarification":
            state["clarification_needed"] = True
            state["clarification_message"] = (
                planned.get("clarification_message")
                or "Could you provide the record identifier (for example INV-000001)?"
            )
            intent = "clarify"
        elif planned.get("follow_up") and not state.get("last_invoice_number"):
            state["clarification_needed"] = True
            state["clarification_message"] = (
                "Which invoice would you like to continue with? "
                "Please provide the invoice number (for example INV-000001)."
            )
            workflow = "clarification"
            intent = "clarify"

        state["intent"] = intent
        state["workflow"] = workflow
        logger.info("Planner route applied: intent '%s' -> workflow '%s'", intent, workflow)
        return state

    intent = classify_intent(question)

    # A follow-up like "what about its payment?" is resolved against the
    # previous invoice, so it must not be treated as a missing-identifier lookup.
    follow_up = bool(state.get("last_invoice_number")) and bool(FOLLOW_UP_RE.search(question))

    if intent in ("find", "query") and not follow_up:
        prompt = clarification_message(question)
        if prompt:
            state["clarification_needed"] = True
            state["clarification_message"] = prompt
            intent = "clarify"

    state["intent"] = intent
    state["workflow"] = INTENT_TO_WORKFLOW.get(intent, "fallback")

    logger.info(f"Classified intent '{intent}' -> workflow '{state['workflow']}'")
    return state
