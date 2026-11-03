"""In-process mock ERP service.

This module is the single source of truth for mock ERP/payment operations.
It is used by:
- the MCP server (``mcp/server.py``), which exposes it over the MCP protocol
- the approval executor, which performs controlled actions after human approval

Keeping the business logic here means the MCP server and the internal executor
cannot diverge, and the mock can later be replaced by a real ERP adapter.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

logger = logging.getLogger(__name__)

_payments: dict[str, dict] = {}
_exceptions: dict[str, dict] = {}
_workflows: dict[str, dict] = {}


def reset_state() -> None:
    """Reset in-memory state (used by tests)."""
    _payments.clear()
    _exceptions.clear()
    _workflows.clear()


def create_payment_request(
    payment_reference: str,
    invoice_id: str,
    amount: float,
    currency: str,
) -> dict:
    """Submit a payment request to the mock ERP."""
    if payment_reference in _payments:
        # Idempotent: return the existing record
        return _payments[payment_reference]

    record = {
        "payment_reference": payment_reference,
        "invoice_id": invoice_id,
        "amount": amount,
        "currency": currency,
        "status": "submitted",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _payments[payment_reference] = record
    logger.info(f"Mock ERP: payment request {payment_reference} created")
    return record


def get_payment_status(payment_reference: str) -> dict | None:
    return _payments.get(payment_reference)


def create_exception(exception_type: str, entity_id: str, description: str) -> dict:
    exception_id = f"EXC-{uuid4().hex[:8].upper()}"
    record = {
        "id": exception_id,
        "exception_type": exception_type,
        "entity_id": entity_id,
        "description": description,
        "status": "open",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _exceptions[exception_id] = record
    logger.info(f"Mock ERP: exception {exception_id} created")
    return record


def update_workflow_status(workflow_id: str, status: str, comment: str | None = None) -> dict:
    record = {
        "id": workflow_id,
        "status": status,
        "comment": comment,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _workflows[workflow_id] = record
    logger.info(f"Mock ERP: workflow {workflow_id} -> {status}")
    return record
