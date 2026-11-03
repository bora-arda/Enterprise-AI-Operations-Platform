"""Checkpointed action-execution graph with human-in-the-loop interrupt.

Lifecycle:
    validate -> policy check -> risk assess -> create approval
             -> interrupt (await human decision)
             -> execute (approve) | record rejection
             -> END

State is persisted with ``AsyncPostgresSaver`` keyed by ``thread_id``. The
thread ID equals the approval UUID, so a pending approval can always be
resumed by its database ID.
"""

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import TypedDict

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import select

from procurement_ai.config.settings import get_settings
from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import ApprovalRequest, Invoice, Payment
from procurement_ai.observability.metrics import APPROVAL_REQUESTS
from procurement_ai.tools.action_tools import execute_approved_action, record_rejection

logger = logging.getLogger(__name__)


class ActionExecutionState(TypedDict, total=False):
    thread_id: str
    user_input: str
    requested_by: str | None
    actor_id: str | None
    invoice_number: str
    invoice_id: str
    amount: float
    currency: str
    risk_level: str
    approvals_needed: str
    approval_id: str
    approval_number: str
    decision: str
    comment: str
    status: str  # awaiting_approval | executed | rejected | blocked
    message: str
    blocked_reason: str


async def validate_node(state: ActionExecutionState) -> dict:
    """Validate the invoice exists, is unpaid, and has no completed payment."""
    question = state.get("user_input", "")
    match = re.search(r"\b(INV-\d+)\b", question, re.IGNORECASE)
    if not match:
        return {
            "status": "blocked",
            "blocked_reason": "No invoice number was provided",
            "message": "I can initiate payment requests, but I need an invoice number.",
        }

    invoice_number = match.group(1).upper()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Invoice).where(Invoice.invoice_number == invoice_number))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return {
                "status": "blocked",
                "blocked_reason": f"Invoice {invoice_number} not found",
                "message": f"I couldn't find invoice {invoice_number}, so no action was taken.",
            }

        result = await session.execute(
            select(Payment).where(
                Payment.invoice_id == invoice.id,
                Payment.status == "completed",
            )
        )
        existing = result.scalars().first()
        if existing:
            return {
                "status": "blocked",
                "blocked_reason": (f"A completed payment already exists ({existing.payment_reference})"),
                "message": (
                    f"Payment request for {invoice_number} was not created. "
                    f"A completed payment already exists ({existing.payment_reference})."
                ),
            }

        if invoice.payment_status == "paid":
            return {
                "status": "blocked",
                "blocked_reason": "Invoice is already marked as paid",
                "message": (
                    f"Payment request for {invoice_number} was not created. The invoice is already marked as paid."
                ),
            }

        return {
            "invoice_number": invoice_number,
            "invoice_id": str(invoice.id),
            "amount": float(invoice.amount),
            "currency": invoice.currency or "GBP",
        }


def route_after_validate(state: ActionExecutionState) -> str:
    return "blocked" if state.get("status") == "blocked" else "valid"


def policy_check_node(state: ActionExecutionState) -> dict:
    """Determine approval requirements from the amount."""
    amount = state.get("amount", 0.0)
    if amount >= 50000:
        needed = "director and finance"
    elif amount >= 10000:
        needed = "manager and finance"
    else:
        needed = "manager"
    return {"approvals_needed": needed}


def risk_assess_node(state: ActionExecutionState) -> dict:
    amount = state.get("amount", 0.0)
    if amount >= 50000:
        risk = "high"
    elif amount >= 10000:
        risk = "medium"
    else:
        risk = "low"
    return {"risk_level": risk}


async def create_approval_node(state: ActionExecutionState) -> dict:
    """Create a pending approval record."""
    approval_id = state["approval_id"]
    approval_number = f"APPR-{uuid.uuid4().hex[:8].upper()}"

    async with AsyncSessionLocal() as session:
        approval = ApprovalRequest(
            id=uuid.UUID(approval_id),
            approval_number=approval_number,
            request_type="payment_request",
            invoice_id=uuid.UUID(state["invoice_id"]),
            requested_by=(uuid.UUID(state["requested_by"]) if state.get("requested_by") else None),
            status="pending",
            justification=(
                f"Payment request for {state['invoice_number']} "
                f"({state['currency']} {state['amount']:,.2f}), risk {state['risk_level']}"
            ),
            requested_at=datetime.now(UTC),
        )
        session.add(approval)
        await session.commit()

    APPROVAL_REQUESTS.labels(status="pending").inc()
    logger.info(f"Created approval {approval_number} for {state['invoice_number']}")
    return {
        "approval_number": approval_number,
        "status": "awaiting_approval",
        "message": f"Approval request {approval_number} is awaiting a human decision.",
    }


async def await_decision_node(state: ActionExecutionState) -> dict:
    """Pause the graph and wait for a human decision."""
    payload = interrupt(
        {
            "type": "approval_required",
            "approval_id": state["approval_id"],
            "approval_number": state["approval_number"],
            "invoice_number": state["invoice_number"],
            "amount": state["amount"],
            "currency": state["currency"],
            "risk_level": state["risk_level"],
            "approvals_needed": state["approvals_needed"],
        }
    )

    if isinstance(payload, dict):
        decision = payload.get("decision", "reject")
        comment = payload.get("comment")
        actor_id = payload.get("actor_id")
    else:
        decision = str(payload)
        comment = None
        actor_id = None

    return {"decision": decision, "comment": comment, "actor_id": actor_id}


def route_after_decision(state: ActionExecutionState) -> str:
    return "approve" if state.get("decision") == "approve" else "reject"


async def execute_node(state: ActionExecutionState) -> dict:
    """Execute the approved payment via the mock ERP."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == uuid.UUID(state["approval_id"]))
        )
        approval = result.scalar_one_or_none()
        if not approval:
            return {
                "status": "blocked",
                "message": "Approval record no longer exists.",
            }

        execution = await execute_approved_action(session, approval, actor_id=state.get("actor_id"))
        if execution["status"] != "executed":
            await session.rollback()
            return {
                "status": "blocked",
                "blocked_reason": execution.get("detail", "execution failed"),
                "message": f"Payment was not executed: {execution.get('detail')}",
            }

        approval.status = "approved"
        approval.decided_at = datetime.now(UTC)
        approval.justification = (approval.justification or "") + f" | Executed: {execution['payment_reference']}"
        await session.commit()

    return {
        "status": "executed",
        "message": (f"Payment executed for {state['invoice_number']}. Reference: {execution['payment_reference']}."),
    }


async def reject_node(state: ActionExecutionState) -> dict:
    """Record a rejected decision."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == uuid.UUID(state["approval_id"]))
        )
        approval = result.scalar_one_or_none()
        if not approval:
            return {"status": "blocked", "message": "Approval record no longer exists."}

        approval.status = "rejected"
        approval.decided_at = datetime.now(UTC)
        if state.get("comment"):
            approval.justification = (approval.justification or "") + f" | Decision: {state['comment']}"
        await record_rejection(session, approval, state.get("comment"), actor_id=state.get("actor_id"))
        await session.commit()

    return {
        "status": "rejected",
        "message": f"Payment request for {state['invoice_number']} was rejected.",
    }


def build_action_graph(checkpointer):
    """Build the action graph with the given checkpointer."""
    graph = StateGraph(ActionExecutionState)

    graph.add_node("validate", validate_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("risk_assess", risk_assess_node)
    graph.add_node("create_approval", create_approval_node)
    graph.add_node("await_decision", await_decision_node)
    graph.add_node("execute", execute_node)
    graph.add_node("reject", reject_node)

    graph.add_edge(START, "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"valid": "policy_check", "blocked": END},
    )
    graph.add_edge("policy_check", "risk_assess")
    graph.add_edge("risk_assess", "create_approval")
    graph.add_edge("create_approval", "await_decision")
    graph.add_conditional_edges(
        "await_decision",
        route_after_decision,
        {"approve": "execute", "reject": "reject"},
    )
    graph.add_edge("execute", END)
    graph.add_edge("reject", END)

    return graph.compile(checkpointer=checkpointer)


# --- Singleton management -------------------------------------------------

_conn_cm = None
_saver: AsyncPostgresSaver | None = None
_graph = None
_lock = asyncio.Lock()


def _checkpoint_dsn() -> str:
    dsn = get_settings().database_url
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


async def _ensure_saver_locked() -> AsyncPostgresSaver:
    """Create the checkpointer once; caller must hold ``_lock``."""
    global _conn_cm, _saver
    if _saver is None:
        _conn_cm = AsyncPostgresSaver.from_conn_string(_checkpoint_dsn())
        _saver = await _conn_cm.__aenter__()
        await _saver.setup()
        logger.info("Initialized Postgres checkpointer")
    return _saver


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return the shared Postgres checkpointer."""
    async with _lock:
        return await _ensure_saver_locked()


async def get_action_graph():
    """Return the singleton action graph backed by Postgres checkpoints."""
    global _graph
    async with _lock:
        if _graph is None:
            saver = await _ensure_saver_locked()
            _graph = build_action_graph(saver)
    return _graph


async def close_action_graph() -> None:
    """Close the checkpointer (used on application shutdown)."""
    global _conn_cm, _saver, _graph
    async with _lock:
        if _conn_cm is not None:
            try:
                await _conn_cm.__aexit__(None, None, None)
            except Exception:
                logger.warning("Error closing checkpointer", exc_info=True)
        _conn_cm = None
        _saver = None
        _graph = None


async def run_action_request(
    user_input: str,
    approval_id: str,
    requested_by: str | None = None,
) -> ActionExecutionState:
    """Start an action workflow; returns after interrupt (awaiting approval)."""
    graph = await get_action_graph()
    state: ActionExecutionState = {
        "thread_id": approval_id,
        "user_input": user_input,
        "requested_by": requested_by,
        "actor_id": None,
        "approval_id": approval_id,
        "decision": "",
        "comment": "",
        "status": "",
        "message": "",
    }
    config = {"configurable": {"thread_id": approval_id}}
    return await graph.ainvoke(state, config=config)


async def resume_action(
    thread_id: str,
    decision: str,
    comment: str | None = None,
    actor_id: str | None = None,
) -> ActionExecutionState:
    """Resume a paused action workflow with a human decision."""
    graph = await get_action_graph()
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke(
        Command(resume={"decision": decision, "comment": comment, "actor_id": actor_id}),
        config=config,
    )


async def has_checkpoint(thread_id: str) -> bool:
    """Check whether this thread has interrupted graph state."""
    graph = await get_action_graph()
    snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    return bool(snapshot and snapshot.values and snapshot.values.get("approval_id") == thread_id)
