"""Action tools for controlled business operations."""

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.database.models import ApprovalRequest, AuditLog, Invoice, Payment
from procurement_ai.mcp import service as erp

logger = logging.getLogger(__name__)


async def create_approval_request(
    session: AsyncSession,
    request_type: str,
    entity_id: str,
    requested_by: str | None,
    justification: str,
) -> dict:
    """Create an approval request row."""
    approval_number = f"APPR-{uuid.uuid4().hex[:8].upper()}"

    approval = ApprovalRequest(
        id=uuid.uuid4(),
        approval_number=approval_number,
        request_type=request_type,
        invoice_id=uuid.UUID(entity_id) if entity_id else None,
        requested_by=None,
        status="pending",
        justification=justification,
        requested_at=datetime.now(UTC),
    )
    session.add(approval)
    await session.flush()

    return {
        "id": str(approval.id),
        "approval_number": approval_number,
        "request_type": request_type,
        "entity_id": entity_id,
        "status": "pending",
        "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
    }


def _actor_uuid(actor_id: str | None) -> uuid.UUID | None:
    if not actor_id:
        return None
    try:
        return uuid.UUID(str(actor_id))
    except (ValueError, TypeError):
        return None


async def execute_approved_action(
    session: AsyncSession,
    approval: ApprovalRequest,
    actor_id: str | None = None,
) -> dict:
    """
    Execute a payment action after human approval.

    Performs a duplicate-payment check, submits the payment to the mock ERP
    service, records the payment, updates the invoice, and writes an audit log.
    """
    if approval.request_type != "payment_request":
        return {
            "status": "unsupported",
            "detail": f"Action type '{approval.request_type}' is not executable",
        }

    if not approval.invoice_id:
        return {"status": "blocked", "detail": "Approval has no associated invoice"}

    result = await session.execute(select(Invoice).where(Invoice.id == approval.invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        return {"status": "blocked", "detail": "Associated invoice no longer exists"}

    # Idempotency / duplicate payment guard
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
            "detail": f"Invoice already has a completed payment ({existing.payment_reference})",
        }

    payment_reference = f"PAY-MCP-{uuid.uuid4().hex[:8].upper()}"
    amount = float(invoice.amount)

    erp_record = erp.create_payment_request(
        payment_reference=payment_reference,
        invoice_id=str(invoice.id),
        amount=amount,
        currency=invoice.currency or "GBP",
    )

    payment = Payment(
        id=uuid.uuid4(),
        payment_reference=payment_reference,
        invoice_id=invoice.id,
        amount=invoice.amount,
        currency=invoice.currency,
        payment_date=date.today(),
        method="mcp_erp",
        status="completed",
    )
    session.add(payment)

    invoice.payment_status = "paid"
    invoice.status = "paid"

    session.add(
        AuditLog(
            id=uuid.uuid4(),
            user_id=_actor_uuid(actor_id),
            action="payment_executed",
            entity_type="invoice",
            entity_id=invoice.invoice_number,
            details={
                "approval_number": approval.approval_number,
                "payment_reference": payment_reference,
                "amount": amount,
                "currency": invoice.currency,
                "erp_status": erp_record.get("status"),
            },
        )
    )

    logger.info(f"Executed approved payment {payment_reference} for {invoice.invoice_number}")

    return {
        "status": "executed",
        "payment_reference": payment_reference,
        "amount": amount,
        "currency": invoice.currency,
        "invoice_number": invoice.invoice_number,
        "erp_status": erp_record.get("status"),
    }


async def record_rejection(
    session: AsyncSession,
    approval: ApprovalRequest,
    comment: str | None,
    actor_id: str | None = None,
) -> None:
    """Write an audit log entry for a rejected action."""
    session.add(
        AuditLog(
            id=uuid.uuid4(),
            user_id=_actor_uuid(actor_id),
            action="payment_rejected",
            entity_type="approval",
            entity_id=approval.approval_number,
            details={"comment": comment},
        )
    )


async def get_approval_status(session: AsyncSession, approval_id: str) -> dict | None:
    """Get the status of an approval request."""
    try:
        result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == uuid.UUID(approval_id)))
    except ValueError:
        return None

    approval = result.scalar_one_or_none()
    if not approval:
        return None

    return {
        "id": str(approval.id),
        "approval_number": approval.approval_number,
        "request_type": approval.request_type,
        "invoice_id": str(approval.invoice_id) if approval.invoice_id else None,
        "status": approval.status,
        "justification": approval.justification,
        "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }
