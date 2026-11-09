"""LLM planner for procurement requests.

The planner converts a natural-language question into a structured route:
workflow, entity reference, semantic metric, clarification, or fallback.

It never executes SQL or tools directly. The deterministic workflows validate
and execute the decision, so the planner can only choose from allow-listed
options. Any failure falls back to the keyword router.
"""

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

from procurement_ai.config.settings import get_settings
from procurement_ai.observability.metrics import LLM_CALLS, LLM_LATENCY, LLM_TOKENS
from procurement_ai.semantic.metrics import ALLOWED_DIMENSIONS, METRIC_LABELS

logger = logging.getLogger(__name__)

WORKFLOWS = {
    "retrieval",
    "investigation",
    "sql",
    "detection",
    "action",
    "clarification",
    "fallback",
}

WORKFLOW_INTENT = {
    "retrieval": "find",
    "investigation": "investigate",
    "sql": "analyze",
    "detection": "detect",
    "action": "act",
    "clarification": "clarify",
    "fallback": "out_of_scope",
}

ENTITY_PREFIXES = {
    "invoice": re.compile(r"^INV-\d+$", re.IGNORECASE),
    "purchase_order": re.compile(r"^PO-\d+$", re.IGNORECASE),
    "contract": re.compile(r"^CF-\d{4}-\d+$", re.IGNORECASE),
    "payment": re.compile(r"^PAY-[A-Za-z0-9-]+$", re.IGNORECASE),
    "approval": re.compile(r"^APPR-[A-Za-z0-9]+$", re.IGNORECASE),
}

PLANNER_PROMPT = """You are the planner for an enterprise procurement operations assistant.
Return ONLY a JSON object with this exact shape:

{
  "workflow": "retrieval | investigation | sql | detection | action | clarification | fallback",
  "intent": "find | investigate | analyze | detect | act | clarify | out_of_scope",
  "entity": {
    "type": "invoice | purchase_order | contract | vendor | payment | approval | null",
    "id": "string or null",
    "name": "string or null"
  },
  "metric": {
    "name": "string or null (see allowed metrics below)",
    "dimension": "vendor | category | department | month | status | exception_type | null",
    "days": "integer or null"
  },
  "follow_up": true | false,
  "clarification_message": "string or null",
  "reason": "short explanation"
}

Allowed metrics:
total_spend, invoice_count, avg_invoice_value, overdue_rate,
exception_count, exception_rate, approval_cycle_time, contracts_expiring,
overdue_invoices, pending_approvals, pending_payment_requests, pending_payments.

Routing rules:
- Specific record lookup by ID (INV-, PO-, CF-, PAY-, APPR-) -> workflow "retrieval", entity type and id.
- Vendor lookup by name (payment terms, contracts, details) -> "retrieval", entity type "vendor", name.
- Why / comply / match / explain / discrepancy about an invoice -> "investigation" with entity invoice.
- Analytics: spending, counts, averages, rates, trends, expiring contracts -> "sql" with a metric.
  Choose a dimension only from the question: vendor, category, department, month, status, exception_type.
  Use days when a time window is stated ("last 30 days", "within 60 days").
- "Which invoices are overdue?" / list overdue invoices -> "sql", metric "overdue_invoices".
- Pending approvals / pending payment requests / pending payments -> "sql":
  "pending_approvals" (all pending approvals, including payment requests),
  "pending_payment_requests" (payment requests only),
  "pending_payments" (payment records in pending/processing status).
- "detailed", "as a table", "each of them", "show those" after a metric answer is a
  follow-up: keep the previous workflow and metric, set follow_up true, and do not
  ask for an invoice identifier.
- Duplicates, anomalies, fraud, policy violations -> "detection".
- Request payment / approve / create exception -> "action" with entity invoice.
- Clarification is ONLY for a single-record lookup missing its identifier. Never ask for
  an invoice when the user asked for a list, aggregate, metric, or table.
- A follow-up that refers to the previous invoice ("its payment", "what about the contract") ->
  follow_up true, entity type "invoice", id null, and the most relevant workflow.
- A detail/table follow-up on a metric answer -> follow_up true, no entity, keep the metric.
- Questions outside procurement/finance -> "fallback", intent "out_of_scope".
- Never invent identifiers. Only use IDs that appear in the question or conversation.

Examples:
Q: "Why is INV-000010 overdue?" ->
{
  "workflow": "investigation",
  "intent": "investigate",
  "entity": {"type": "invoice", "id": "INV-000010", "name": null},
  "metric": {"name": null, "dimension": null, "days": null},
  "follow_up": false,
  "clarification_message": null,
  "reason": "invoice investigation"
}

Q: "Who is generating the most exceptions?" ->
{
  "workflow": "sql",
  "intent": "analyze",
  "entity": {"type": null, "id": null, "name": null},
  "metric": {"name": "exception_count", "dimension": "vendor", "days": null},
  "follow_up": false,
  "clarification_message": null,
  "reason": "exception analytics by vendor"
}

Q: "Show me purchase order PO-000001" ->
{
  "workflow": "retrieval",
  "intent": "find",
  "entity": {"type": "purchase_order", "id": "PO-000001", "name": null},
  "metric": {"name": null, "dimension": null, "days": null},
  "follow_up": false,
  "clarification_message": null,
  "reason": "direct PO lookup"
}

Q: "What about its payment?" (previous invoice INV-000010) ->
{
  "workflow": "retrieval",
  "intent": "find",
  "entity": {"type": "invoice", "id": null, "name": null},
  "metric": {"name": null, "dimension": null, "days": null},
  "follow_up": true,
  "clarification_message": null,
  "reason": "follow-up on previous invoice"
}

Q: "Which payment requests are pending?" ->
{
  "workflow": "sql",
  "intent": "analyze",
  "entity": {"type": null, "id": null, "name": null},
  "metric": {"name": "pending_payment_requests", "dimension": null, "days": null},
  "follow_up": false,
  "clarification_message": null,
  "reason": "list pending payment requests"
}

Q: "List all pending payments and approvals detailed as a table" ->
{
  "workflow": "sql",
  "intent": "analyze",
  "entity": {"type": null, "id": null, "name": null},
  "metric": {"name": "pending_approvals", "dimension": null, "days": null},
  "follow_up": false,
  "clarification_message": null,
  "reason": "detailed pending approvals table"
}
"""


@dataclass
class PlannerDecision:
    workflow: str
    intent: str
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None
    metric: str | None = None
    dimension: str | None = None
    days: int | None = None
    follow_up: bool = False
    clarification_message: str | None = None
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def validate_decision(payload: dict | None) -> PlannerDecision | None:
    """Validate and constrain a planner payload to allow-listed options."""
    if not isinstance(payload, dict):
        return None

    workflow = str(payload.get("workflow", "")).lower().strip()
    if workflow not in WORKFLOWS:
        return None

    intent = str(payload.get("intent", "")).lower().strip()
    if intent not in set(WORKFLOW_INTENT.values()):
        intent = WORKFLOW_INTENT[workflow]

    entity = payload.get("entity") or {}
    if not isinstance(entity, dict):
        entity = {}
    entity_type = str(entity.get("type") or "").lower().strip() or None
    entity_id = str(entity.get("id") or "").strip().upper() or None
    entity_name = str(entity.get("name") or "").strip()[:120] or None

    if entity_type not in ENTITY_PREFIXES:
        entity_type, entity_id, entity_name = None, None, None
    elif entity_id and not ENTITY_PREFIXES[entity_type].match(entity_id):
        entity_id = None

    metric = payload.get("metric") or {}
    if not isinstance(metric, dict):
        metric = {}
    metric_name = str(metric.get("name") or "").lower().strip() or None
    dimension = str(metric.get("dimension") or "").lower().strip() or None
    days_raw = metric.get("days")

    if metric_name not in METRIC_LABELS:
        metric_name, dimension, days = None, None, None
    else:
        allowed = ALLOWED_DIMENSIONS.get(metric_name, set())
        if dimension not in allowed:
            dimension = None
        try:
            days = int(days_raw) if days_raw is not None else None
        except (TypeError, ValueError):
            days = None
        if days is not None and not (1 <= days <= 3650):
            days = None

    clarification = str(payload.get("clarification_message") or "").strip()[:300] or None
    if workflow == "clarification" and not clarification:
        clarification = "Could you provide the record identifier (for example INV-000001)?"

    return PlannerDecision(
        workflow=workflow,
        intent=intent,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        metric=metric_name,
        dimension=dimension,
        days=days,
        follow_up=bool(payload.get("follow_up")),
        clarification_message=clarification,
        reason=str(payload.get("reason") or "")[:200],
    )


def _history_excerpt(history: list[dict] | None, limit: int = 6) -> str:
    if not history:
        return ""
    lines = []
    for message in history[-limit:]:
        role = message.get("role", "user")
        content = str(message.get("content", ""))[:400]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


@dataclass
class PlannerOutcome:
    """Decision plus audit metadata for the planner call."""

    decision: PlannerDecision | None
    planner_mode: str
    model: str | None = None
    validation_result: str = "not_applicable"
    fallback_used: bool = False
    raw_decision: dict | None = None
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None


async def plan_request(
    question: str,
    history: list[dict] | None = None,
    previous_route: dict | None = None,
) -> PlannerOutcome:
    """Ask Claude Haiku for a structured route, with audit metadata."""
    settings = get_settings()
    mode = settings.planner_mode.lower()
    model = settings.opencode_go_model

    if mode != "llm":
        return PlannerOutcome(
            decision=None,
            planner_mode=mode,
            model=None,
            validation_result="deterministic",
            fallback_used=False,
        )

    if not settings.opencode_go_api_key:
        return PlannerOutcome(
            decision=None,
            planner_mode=mode,
            model=model,
            validation_result="missing_api_key",
            fallback_used=True,
        )

    client = AsyncOpenAI(
        api_key=settings.opencode_go_api_key,
        base_url=settings.opencode_go_base_url,
        default_headers={"x-opencode-session": settings.opencode_session_id},
        timeout=settings.llm_timeout_seconds,
        max_retries=1,
    )

    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": PLANNER_PROMPT}]
    history_text = _history_excerpt(history)
    if history_text:
        messages.append(
            {
                "role": "system",
                "content": "Recent conversation (for follow-up resolution):\n" + history_text,
            }
        )
    if previous_route:
        messages.append(
            {
                "role": "system",
                "content": "Previous routing decision (for detail/table follow-ups):\n"
                + json.dumps(previous_route, default=str),
            }
        )
    messages.append({"role": "user", "content": question})

    start = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=500,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        if usage is not None:
            record_usage(input_tokens, output_tokens)

        payload = _extract_json(text)
        decision = validate_decision(payload)
        validation_result = "accepted" if decision else "rejected"
        if decision is None:
            logger.warning("Planner returned an invalid decision: %s", text[:300])

        return PlannerOutcome(
            decision=decision,
            planner_mode=mode,
            model=model,
            validation_result=validation_result,
            fallback_used=decision is None,
            raw_decision=payload,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(f"LLM planner failed, falling back to deterministic routing: {e}")
        return PlannerOutcome(
            decision=None,
            planner_mode=mode,
            model=model,
            validation_result="error",
            fallback_used=True,
            latency_ms=latency_ms,
        )
    finally:
        LLM_LATENCY.labels(provider="opencode_go", model=model).observe(time.perf_counter() - start)
        LLM_CALLS.labels(provider="opencode_go").inc()


def record_usage(prompt_tokens: int | None, completion_tokens: int | None) -> None:
    """Record token usage from a planner response."""
    if prompt_tokens:
        LLM_TOKENS.labels(type="input").inc(prompt_tokens)
    if completion_tokens:
        LLM_TOKENS.labels(type="output").inc(completion_tokens)
