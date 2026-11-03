"""Action workflow node.

Delegates to the checkpointed action-execution graph:
validate -> policy -> risk -> create approval -> interrupt.

The graph pauses at ``interrupt()`` and is resumed later via the approvals API.
"""

import logging
import re
import uuid

from procurement_ai.graph.action_execution import run_action_request

logger = logging.getLogger(__name__)


async def action_workflow_node(state: dict) -> dict:
    """Start an action request and return the awaiting-approval response."""
    question = state.get("user_input", "")
    planned = state.get("planned_route") or {}

    if planned.get("entity_type") == "invoice" and planned.get("entity_id"):
        question = f"{question} {planned['entity_id']}"

    if not re.search(r"\b(INV-\d+)\b", question, re.IGNORECASE):
        state["response"] = (
            "I can initiate controlled actions such as payment requests, but I need "
            "the invoice number (for example, INV-000001)."
        )
        state["confidence"] = 0.3
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
