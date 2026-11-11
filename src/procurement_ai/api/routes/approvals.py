"""Approval workflow endpoints backed by the approval_requests table.

Pending approvals created by the checkpointed action graph are resumed through
LangGraph ``Command(resume=...)``. Legacy approvals without graph state fall
back to direct execution.
"""

import logging
import re
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.api.dependencies import get_db_session
from procurement_ai.api.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
)
from procurement_ai.auth.dependencies import (
    APPROVER_ROLES,
    AuthUser,
    get_current_user,
    require_roles,
)
from procurement_ai.database.models import (
    ApprovalRequest,
    Department,
    Invoice,
    PurchaseOrder,
    User,
    Vendor,
)
from procurement_ai.graph.action_execution import has_checkpoint, resume_action
from procurement_ai.observability.metrics import APPROVAL_REQUESTS
from procurement_ai.tools.action_tools import execute_approved_action, record_rejection

logger = logging.getLogger(__name__)
router = APIRouter()


def _risk_level(row: ApprovalRequest, amount: float | None) -> str:
    match = re.search(r"\brisk\s+(high|medium|low)\b", row.justification or "", re.IGNORECASE)
    if match:
        return match.group(1).lower()
    if amount is None:
        return "medium"
    if amount >= 50_000:
        return "high"
    if amount >= 10_000:
        return "medium"
    return "low"


def _to_response(
    row: ApprovalRequest,
    invoice: Invoice | None = None,
    vendor: Vendor | None = None,
    requester: User | None = None,
    department: Department | None = None,
) -> ApprovalResponse:
    amount = float(invoice.amount) if invoice and invoice.amount is not None else None
    return ApprovalResponse(
        id=str(row.id),
        approval_number=row.approval_number,
        request_type=row.request_type or "",
        invoice_id=str(row.invoice_id) if row.invoice_id else None,
        invoice_number=invoice.invoice_number if invoice else None,
        amount=amount,
        currency=invoice.currency if invoice else None,
        vendor_name=vendor.name if vendor else None,
        requested_by_name=requester.name if requester else None,
        department_name=department.name if department else None,
        department_code=department.code if department else None,
        due_date=invoice.due_date.isoformat() if invoice and invoice.due_date else None,
        risk_level=_risk_level(row, amount),
        status=row.status or "pending",
        requested_at=row.requested_at.isoformat() if row.requested_at else None,
        decided_at=row.decided_at.isoformat() if row.decided_at else None,
        justification=row.justification,
    )


def _approval_query():
    return (
        select(ApprovalRequest, Invoice, Vendor, User, Department)
        .outerjoin(Invoice, Invoice.id == ApprovalRequest.invoice_id)
        .outerjoin(Vendor, Vendor.id == Invoice.vendor_id)
        .outerjoin(User, User.id == ApprovalRequest.requested_by)
        .outerjoin(PurchaseOrder, PurchaseOrder.id == Invoice.po_id)
        .outerjoin(Department, Department.id == PurchaseOrder.department_id)
    )


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    status: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
    user: AuthUser = Depends(get_current_user),
):
    """List approval requests with related invoice and vendor context."""
    query = _approval_query()
    if status:
        query = query.where(ApprovalRequest.status == status)
    query = query.order_by(ApprovalRequest.requested_at.desc()).limit(limit)

    result = await session.execute(query)
    rows = result.all()

    return ApprovalListResponse(
        approvals=[
            _to_response(
                approval,
                invoice=invoice,
                vendor=vendor,
                requester=requester,
                department=department,
            )
            for approval, invoice, vendor, requester, department in rows
        ],
        total=len(rows),
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: AuthUser = Depends(get_current_user),
):
    """Get a single approval request with related context."""
    try:
        result = await session.execute(_approval_query().where(ApprovalRequest.id == UUID(approval_id)))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID") from None

    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval, invoice, vendor, requester, department = row
    return _to_response(
        approval,
        invoice=invoice,
        vendor=vendor,
        requester=requester,
        department=department,
    )


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db_session),
    user: AuthUser = Depends(require_roles(*APPROVER_ROLES)),
):
    """
    Approve or reject a pending request.

    If the approval was created by the checkpointed action graph, the graph is
    resumed with the human decision, which executes or rejects the payment and
    updates the approval. Otherwise, the action is executed directly.
    """
    try:
        result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == UUID(approval_id)))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID") from None

    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")

    if row.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval is already '{row.status}' and cannot be changed",
        )

    # Separation of duties: no self-approval
    if row.requested_by and str(row.requested_by) == user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot decide an approval you requested",
        )

    # Resumable path: graph state exists for this approval thread
    try:
        resumable = await has_checkpoint(str(row.id))
    except Exception:
        logger.warning("Checkpointer unavailable; using direct execution", exc_info=True)
        resumable = False

    if resumable:
        try:
            await resume_action(
                str(row.id),
                request.decision,
                request.comment,
                actor_id=user.id,
            )
        except Exception as e:
            logger.error(f"Graph resume failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to resume approval workflow",
            ) from e

        await session.refresh(row)
        if row.status == "approved":
            with suppress(ValueError):
                row.approved_by = UUID(user.id)
            await session.commit()
            await session.refresh(row)
        APPROVAL_REQUESTS.labels(status=row.status or "unknown").inc()
        logger.info(f"Approval {row.approval_number} resumed: {row.status}")
        return _to_response(row)

    # Legacy fallback: direct execution without graph state
    if request.decision == "approve":
        execution = await execute_approved_action(session, row, actor_id=user.id)
        if execution["status"] == "blocked":
            await session.rollback()
            raise HTTPException(status_code=409, detail=execution["detail"])
        if execution["status"] != "executed":
            await session.rollback()
            raise HTTPException(status_code=422, detail=execution["detail"])
        row.status = "approved"
        with suppress(ValueError):
            row.approved_by = UUID(user.id)
        row.justification = (row.justification or "") + f" | Executed: {execution['payment_reference']}"
    else:
        row.status = "rejected"
        await record_rejection(session, row, request.comment, actor_id=user.id)
        if request.comment:
            row.justification = (row.justification or "") + f" | Decision: {request.comment}"

    row.decided_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(row)

    APPROVAL_REQUESTS.labels(status=row.status or "unknown").inc()
    logger.info(f"Approval {row.approval_number} decided (direct): {row.status}")
    return _to_response(row)
