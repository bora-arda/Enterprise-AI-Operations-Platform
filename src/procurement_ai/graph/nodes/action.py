"""Action workflow node.

Delegates to the checkpointed action-execution graph:
validate -> policy -> risk -> create approval -> interrupt.

The graph pauses at ``interrupt()`` and is resumed later via the approvals API.
"""

import logging
import re
import uuid

from sqlalchemy import select

from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import Invoice, PurchaseOrder
from procurement_ai.graph.action_execution import run_action_request
from procurement_ai.security.access import scope_from_state

logger = logging.getLogger(__name__)


async def action_workflow_node(state: dict) -> dict:
    """Start an action request and return the awaiting-approval response."""
    question = state.get("user_input", "")
    planned = state.get("planned_route") or {}

    if planned.get("entity_type") == "invoice" and planned.get("entity_id"):
        question = f"{question} {planned['entity_id']}"

    match = re.search(r"\b(INV-\d+)\b", question, re.IGNORECASE)
    if not match:
        state["response"] = (
            "I can initiate controlled actions such as payment requests, but I need "
            "the invoice number (for example, INV-000001)."
        )
        state["confidence"] = 0.3
        return state

    scope = scope_from_state(state)
    if scope.restricted:
        async with AsyncSessionLocal() as session:
            scope_result = await session.execute(
                select(PurchaseOrder.department_id)
                .join(Invoice, Invoice.po_id == PurchaseOrder.id)
                .where(Invoice.invoice_number == match.group(1).upper())
            )
            department_id = scope_result.scalar_one_or_none()
        if not scope.allows_department(department_id):
            state["response"] = (
                "I couldn't find an invoice with that reference in your department, so no action was taken."
            )
            state["confidence"] = 0.3
            state["workflow"] = "action"
            return state

    approval_id = str(uuid.uuid4())

    try:
        result = await run_action_request(
            question,
            approval_id=approval_id,
            requested_by=state.get("user_id"),
        )
    except Exception as e:
        logger.error(f"Action graph failed: {e}", exc_info=True)
        state["response"] = "I encountered an error while processing your action request."
        state["errors"] = state.get("errors", []) + [str(e)]
        return state

    status = result.get("status", "")
    invoice_number = result.get("invoice_number", "")
    approval_number = result.get("approval_number", "")

    if status == "blocked":
        state["response"] = result.get("message", "The action was blocked.")
        state["confidence"] = 0.9
        state["workflow"] = "action"
        state["approval_status"] = "not_required"
        return state

    if status == "awaiting_approval":
        risk = result.get("risk_level", "unknown")
        needed = result.get("approvals_needed", "a manager")
        amount = result.get("amount", 0.0)
        currency = result.get("currency", "GBP")

        state["response"] = (
            f"A payment approval request has been created for {invoice_number}.\n\n"
            f"- Approval reference: {approval_number}\n"
            f"- Amount: {currency} {amount:,.2f}\n"
            f"- Risk level: {risk}\n"
            f"- Required approvers: {needed}\n\n"
            f"The payment will not be executed until a human approves this request."
        )
        state["citations"] = [
            {
                "source": f"invoice:{invoice_number}",
                "snippet": f"Amount {amount:,.2f} {currency}",
            },
            {
                "source": f"approval:{approval_number}",
                "snippet": f"Status pending, risk {risk}",
            },
        ]
        state["evidence"] = [
            {
                "source": f"approval:{approval_number}",
                "content": "pending",
                "metadata": {"risk": risk, "approval_id": approval_id},
            }
        ]
        state["approval_status"] = "pending"
        state["confidence"] = 0.95
        state["workflow"] = "action"
        state["tool_results"] = state.get("tool_results", []) + [
            {
                "tool_name": "create_approval_request",
                "success": True,
                "result": {"approval_number": approval_number, "risk": risk},
                "error": None,
            }
        ]
        return state

    state["response"] = result.get("message", "The action completed.")
    state["workflow"] = "action"
    state["approval_status"] = "not_required"
    return state
