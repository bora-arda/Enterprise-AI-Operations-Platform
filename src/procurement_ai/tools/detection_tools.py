"""Anomaly detection tools."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.anomaly_detection.rules import run_all_rules
from procurement_ai.database.models import (
    ApprovalRequest,
    Contract,
    Invoice,
    Payment,
    PurchaseOrder,
)

logger = logging.getLogger(__name__)


def _chunks(items: list, size: int = 5000):
    """Yield successive chunks to stay under database parameter limits."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def detect_anomalies(
    session: AsyncSession,
    entity_type: str = "invoice",
    entity_id: str | None = None,
    limit: int = 300,
) -> list[dict]:
    """Run anomaly detection on invoices."""
    if entity_type != "invoice":
        raise ValueError(f"Unsupported entity type: {entity_type}")

    # Load invoices
    if entity_id:
        result = await session.execute(select(Invoice).where(Invoice.id == entity_id))
        invoices = result.scalars().all()
    else:
        result = await session.execute(select(Invoice).limit(limit))
        invoices = result.scalars().all()

    # Load related data
    po_ids = [inv.po_id for inv in invoices if inv.po_id]
    pos: dict[str, dict] = {}
    for chunk in _chunks(po_ids):
        result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id.in_(chunk)))
        for po_row in result.scalars().all():
            pos[str(po_row.id)] = {
                "id": str(po_row.id),
                "po_number": po_row.po_number,
                "vendor_id": str(po_row.vendor_id),
                "contract_id": str(po_row.contract_id) if po_row.contract_id else None,
                "total_amount": float(po_row.total_amount),
                "currency": po_row.currency,
            }

    # Load contracts
    contract_ids = [p["contract_id"] for p in pos.values() if p.get("contract_id")]
    contracts: dict[str, dict] = {}
    if contract_ids:
        from uuid import UUID

        uuid_ids = [UUID(c) for c in contract_ids]
        for chunk in _chunks(uuid_ids):
            result = await session.execute(select(Contract).where(Contract.id.in_(chunk)))
            for contract_row in result.scalars().all():
                contracts[str(contract_row.id)] = {
                    "id": str(contract_row.id),
                    "max_value": float(contract_row.max_value) if contract_row.max_value else None,
                    "end_date": contract_row.end_date.isoformat() if contract_row.end_date else None,
                }

    # Load approvals and payments for these invoices
    invoice_ids = [inv.id for inv in invoices]
    approvals_by_invoice: dict = {}
    payments_by_invoice: dict = {}
    for chunk in _chunks(invoice_ids):
        result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.invoice_id.in_(chunk)))
        for approval in result.scalars().all():
            approvals_by_invoice.setdefault(approval.invoice_id, []).append(
                {"invoice_id": str(approval.invoice_id), "status": approval.status}
            )

        result = await session.execute(select(Payment).where(Payment.invoice_id.in_(chunk)))
        for payment in result.scalars().all():
            payments_by_invoice.setdefault(payment.invoice_id, []).append(payment)

    # Run rules
    anomalies = []
    for inv in invoices:
        inv_dict = {
            "id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "amount": float(inv.amount),
            "currency": inv.currency,
            "vendor_id": str(inv.vendor_id),
            "po_id": str(inv.po_id) if inv.po_id else None,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv.status,
        }

        po = pos.get(str(inv.po_id)) if inv.po_id else None
        contract = contracts.get(po.get("contract_id") or "") if po else None

        # Invalid / missing PO reference
        if inv.po_id is None:
            anomalies.append(
                {
                    "rule": "invalid_po",
                    "severity": "high",
                    "description": f"Invoice {inv.invoice_number} has no valid purchase order",
                    "details": {"invoice_id": str(inv.id)},
                    "invoice_id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                }
            )

        inv_approvals = approvals_by_invoice.get(inv.id, [])
        inv_anomalies = run_all_rules(inv_dict, po, contract, inv_approvals)
        for anomaly in inv_anomalies:
            anomaly["invoice_id"] = str(inv.id)
            anomaly["invoice_number"] = inv.invoice_number
            anomalies.append(anomaly)

        completed_payments = [p for p in payments_by_invoice.get(inv.id, []) if p.status == "completed"]

        # Duplicate payment on an already-paid invoice
        if len(completed_payments) > 1:
            anomalies.append(
                {
                    "rule": "already_paid",
                    "severity": "high",
                    "description": (f"Invoice {inv.invoice_number} has {len(completed_payments)} completed payments"),
                    "details": {"payment_references": [p.payment_reference for p in completed_payments]},
                    "invoice_id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                }
            )

        # Payment amount mismatch
        for payment in completed_payments:
            if abs(float(payment.amount) - float(inv.amount)) > 0.01:
                anomalies.append(
                    {
                        "rule": "payment_mismatch",
                        "severity": "high",
                        "description": (
                            f"Payment {payment.payment_reference} amount "
                            f"({float(payment.amount):,.2f}) does not match invoice "
                            f"{inv.invoice_number} amount ({float(inv.amount):,.2f})"
                        ),
                        "details": {
                            "payment_reference": payment.payment_reference,
                            "payment_amount": float(payment.amount),
                            "invoice_amount": float(inv.amount),
                        },
                        "invoice_id": str(inv.id),
                        "invoice_number": inv.invoice_number,
                    }
                )

    return anomalies


async def detect_duplicates(session: AsyncSession, limit: int = 5000) -> list[dict]:
    """
    Detect potential duplicate invoices.

    Heuristic: same vendor and (nearly) same amount within a 7-day window.
    """

    result = await session.execute(select(Invoice).limit(limit))
    invoices = list(result.scalars().all())

    groups: dict[tuple, list] = {}
    for inv in invoices:
        if inv.vendor_id is None or inv.amount is None:
            continue
        key = (str(inv.vendor_id), round(float(inv.amount), 2))
        groups.setdefault(key, []).append(inv)

    duplicates: list[dict] = []
    for (vendor_id, amount), group in groups.items():
        if len(group) < 2:
            continue
        # Check for date proximity within the group
        flagged = False
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                d1, d2 = group[i].invoice_date, group[j].invoice_date
                if d1 and d2 and abs((d1 - d2).days) <= 7:
                    flagged = True
                    break
            if flagged:
                break

        if flagged:
            duplicates.append(
                {
                    "rule": "duplicate_invoice",
                    "severity": "high",
                    "description": (
                        f"{len(group)} invoices for the same vendor and amount "
                        f"({amount:,.2f}) within 7 days: " + ", ".join(inv.invoice_number for inv in group)
                    ),
                    "invoice_id": str(group[0].id),
                    "invoice_numbers": [inv.invoice_number for inv in group],
                    "details": {
                        "vendor_id": vendor_id,
                        "amount": amount,
                        "invoice_numbers": [inv.invoice_number for inv in group],
                    },
                }
            )

    return duplicates


async def check_policy(session: AsyncSession, entity_type: str, entity_id: str) -> dict:
    """Check policy compliance for an entity."""
    if entity_type != "invoice":
        raise ValueError(f"Unsupported entity type: {entity_type}")

    result = await session.execute(select(Invoice).where(Invoice.id == entity_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        return {"error": "Invoice not found"}

    # Load related data
    po_result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == invoice.po_id))
    po = po_result.scalar_one_or_none()

    contract = None
    if po:
        contract_result = await session.execute(select(Contract).where(Contract.id == po.contract_id))
        contract = contract_result.scalar_one_or_none()

    # Run checks
    anomalies = run_all_rules(
        {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "amount": float(invoice.amount),
            "currency": invoice.currency,
            "vendor_id": str(invoice.vendor_id),
            "po_id": str(invoice.po_id) if invoice.po_id else None,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "status": invoice.status,
        },
        {
            "id": str(po.id),
            "po_number": po.po_number,
            "vendor_id": str(po.vendor_id),
            "total_amount": float(po.total_amount),
            "currency": po.currency,
        }
        if po
        else None,
        {
            "id": str(contract.id),
            "max_value": float(contract.max_value) if contract.max_value else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
        }
        if contract
        else None,
        [],
    )

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "compliant": len(anomalies) == 0,
        "anomalies": anomalies,
    }
