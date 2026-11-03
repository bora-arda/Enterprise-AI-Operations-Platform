"""First-class entity lookups across procurement records.

Handles direct references such as INV-000001, PO-000123, CF-2022-00001,
PAY-000123, APPR-XXXXXXXX, vendor name searches, and simple follow-ups
that refer back to the previous invoice.
"""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import func, select

from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import (
    ApprovalRequest,
    Buyer,
    Contract,
    Department,
    Invoice,
    Payment,
    PurchaseOrder,
    Vendor,
)
from procurement_ai.graph.nodes.entities import (
    extract_entity_id,
)
from procurement_ai.graph.nodes.entities import (
    extract_vendor_name as _extract_vendor_name,
)
from procurement_ai.graph.nodes.investigation import _build_response, _load_invoice_bundle

logger = logging.getLogger(__name__)

FOLLOW_UP = re.compile(
    r"\b(it|its|that|this|the same|previous)\b|\bwhat about\b|\band the\b",
    re.IGNORECASE,
)


@dataclass
class EntityResult:
    response: str
    citations: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    invoice_number: str | None = None


def _fmt(amount, currency: str | None = "GBP") -> str:
    if amount is None:
        return "unknown"
    return f"{currency or ''} {float(amount):,.2f}".strip()


def extract_entity_reference(question: str) -> tuple[str, str] | None:
    """Extract a typed entity reference (single source of truth: entities.py)."""
    return extract_entity_id(question)


def extract_vendor_name(question: str) -> str | None:
    """Extract a vendor name (single source of truth: entities.py)."""
    return _extract_vendor_name(question)


async def _invoice_lookup(invoice_number: str) -> EntityResult | None:
    bundle = await _load_invoice_bundle(invoice_number)
    if not bundle:
        return None
    response, citations, evidence = _build_response(bundle)
    return EntityResult(
        response=response,
        citations=citations,
        evidence=evidence,
        invoice_number=invoice_number,
    )


async def _po_lookup(po_number: str) -> EntityResult | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == po_number))
        po = result.scalar_one_or_none()
        if not po:
            return None

        vendor = None
        if po.vendor_id:
            vendor = (await session.execute(select(Vendor).where(Vendor.id == po.vendor_id))).scalar_one_or_none()

        contract = None
        if po.contract_id:
            contract = (
                await session.execute(select(Contract).where(Contract.id == po.contract_id))
            ).scalar_one_or_none()

        dept = None
        if po.department_id:
            dept = (
                await session.execute(select(Department).where(Department.id == po.department_id))
            ).scalar_one_or_none()

        agg = (
            await session.execute(
                select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0)).where(Invoice.po_id == po.id)
            )
        ).one()

    lines = [
        f"Purchase order {po.po_number}",
        f"- Vendor: {vendor.name if vendor else 'unknown'}",
        f"- Department: {dept.name if dept else 'unassigned'}",
        f"- Contract: {contract.contract_number if contract else 'none'}",
        f"- Total amount: {_fmt(po.total_amount, po.currency)}",
        f"- Status: {po.status}",
        f"- Ordered: {po.order_date} / delivery: {po.delivery_date}",
        f"- Linked invoices: {agg[0]} totalling {_fmt(agg[1], po.currency)}",
    ]

    citations = [
        {
            "source": f"purchase_order:{po.po_number}",
            "snippet": f"{_fmt(po.total_amount, po.currency)}, status={po.status}",
        }
    ]
    if contract:
        citations.append(
            {
                "source": f"contract:{contract.contract_number}",
                "snippet": contract.title,
            }
        )

    return EntityResult(
        response="\n".join(lines),
        citations=citations,
        evidence=[
            {
                "source": f"purchase_order:{po.po_number}",
                "content": "\n".join(lines),
                "metadata": {},
            }
        ],
    )


async def _contract_lookup(contract_number: str) -> EntityResult | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Contract).where(Contract.contract_number == contract_number))
        contract = result.scalar_one_or_none()
        if not contract:
            return None

        vendor = None
        if contract.vendor_id:
            vendor = (await session.execute(select(Vendor).where(Vendor.id == contract.vendor_id))).scalar_one_or_none()

        buyer = None
        if contract.buyer_id:
            buyer = (await session.execute(select(Buyer).where(Buyer.id == contract.buyer_id))).scalar_one_or_none()

        po_count = (
            await session.execute(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.contract_id == contract.id))
        ).scalar()

        invoice_total = (
            await session.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0))
                .join(PurchaseOrder, PurchaseOrder.id == Invoice.po_id)
                .where(PurchaseOrder.contract_id == contract.id)
            )
        ).scalar()

    lines = [
        f"Contract {contract.contract_number}: {contract.title}",
        f"- Vendor: {vendor.name if vendor else 'unknown'}",
        f"- Buyer: {buyer.name if buyer else 'unknown'}",
        f"- Value: {_fmt(contract.value, contract.currency)} (maximum {_fmt(contract.max_value, contract.currency)})",
        f"- Period: {contract.start_date} to {contract.end_date}",
        f"- Category: {contract.category_description or contract.category or 'n/a'}",
        f"- Status: {contract.status}",
        f"- Purchase orders: {po_count}",
        f"- Invoiced to date: {_fmt(invoice_total, contract.currency)}",
    ]

    return EntityResult(
        response="\n".join(lines),
        citations=[
            {
                "source": f"contract:{contract.contract_number}",
                "snippet": f"{contract.title}, {_fmt(contract.max_value, contract.currency)}",
            }
        ],
        evidence=[
            {
                "source": f"contract:{contract.contract_number}",
                "content": "\n".join(lines),
                "metadata": {},
            }
        ],
    )


async def _payment_lookup(reference: str) -> EntityResult | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Payment).where(Payment.payment_reference == reference))
        payment = result.scalar_one_or_none()
        if not payment:
            return None

        invoice = None
        vendor = None
        if payment.invoice_id:
            invoice = (
                await session.execute(select(Invoice).where(Invoice.id == payment.invoice_id))
            ).scalar_one_or_none()
            if invoice and invoice.vendor_id:
                vendor = (
                    await session.execute(select(Vendor).where(Vendor.id == invoice.vendor_id))
                ).scalar_one_or_none()

    lines = [
        f"Payment {payment.payment_reference}",
        f"- Amount: {_fmt(payment.amount, payment.currency)}",
        f"- Status: {payment.status}",
        f"- Date: {payment.payment_date}",
        f"- Method: {payment.method}",
        f"- Invoice: {invoice.invoice_number if invoice else 'unknown'}",
        f"- Vendor: {vendor.name if vendor else 'unknown'}",
    ]

    return EntityResult(
        response="\n".join(lines),
        citations=[
            {
                "source": f"payment:{payment.payment_reference}",
                "snippet": f"{_fmt(payment.amount, payment.currency)}, status={payment.status}",
            }
        ],
        evidence=[
            {
                "source": f"payment:{payment.payment_reference}",
                "content": "\n".join(lines),
                "metadata": {},
            }
        ],
    )


async def _approval_lookup(reference: str) -> EntityResult | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.approval_number == reference))
        approval = result.scalar_one_or_none()
        if not approval:
            return None

        invoice = None
        if approval.invoice_id:
            invoice = (
                await session.execute(select(Invoice).where(Invoice.id == approval.invoice_id))
            ).scalar_one_or_none()

    lines = [
        f"Approval {approval.approval_number}",
        f"- Type: {approval.request_type}",
        f"- Status: {approval.status}",
        f"- Invoice: {invoice.invoice_number if invoice else 'unknown'}",
        f"- Requested: {approval.requested_at}",
        f"- Decided: {approval.decided_at}",
        f"- Justification: {approval.justification or 'n/a'}",
    ]

    return EntityResult(
        response="\n".join(lines),
        citations=[
            {
                "source": f"approval:{approval.approval_number}",
                "snippet": f"status={approval.status}",
            }
        ],
        evidence=[
            {
                "source": f"approval:{approval.approval_number}",
                "content": "\n".join(lines),
                "metadata": {},
            }
        ],
    )


async def _vendor_lookup(name: str) -> EntityResult | None:
    async with AsyncSessionLocal() as session:
        # Prefer an exact (case-insensitive) match before fuzzy candidates.
        exact_result = await session.execute(select(Vendor).where(func.lower(Vendor.name) == name.lower()).limit(1))
        exact_vendor = exact_result.scalars().first()

        if exact_vendor:
            vendors = [exact_vendor]
        else:
            result = await session.execute(select(Vendor).where(Vendor.name.ilike(f"%{name}%")).limit(6))
            vendors = list(result.scalars().all())

    if not vendors:
        return None

    if len(vendors) > 1:
        lines = [f"I found {len(vendors)} vendors matching '{name}':"]
        for vendor in vendors[:5]:
            lines.append(f"- {vendor.name} ({vendor.id})")
        lines.append("Please specify which vendor you mean.")
        return EntityResult(response="\n".join(lines))

    vendor = vendors[0]

    async with AsyncSessionLocal() as session:
        contracts = list(
            (
                await session.execute(
                    select(Contract)
                    .where(Contract.vendor_id == vendor.id)
                    .order_by(Contract.end_date.desc().nullslast())
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )
        po_count = (
            await session.execute(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.vendor_id == vendor.id))
        ).scalar()
        invoice_total = (
            await session.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0)).where(Invoice.vendor_id == vendor.id)
            )
        ).scalar()

    lines = [
        f"Vendor {vendor.name} ({vendor.id})",
        f"- Country: {vendor.country or 'unknown'}",
        f"- Status: {vendor.status or 'unknown'}",
        f"- Purchase orders: {po_count}",
        f"- Invoiced total: {_fmt(invoice_total)}",
    ]
    if contracts:
        lines.append("- Contracts:")
        for contract in contracts:
            lines.append(
                f"  • {contract.contract_number}: {contract.title} "
                f"({contract.start_date} to {contract.end_date}, "
                f"{_fmt(contract.max_value, contract.currency)})"
            )
    else:
        lines.append("- Contracts: none on record")

    citations = [{"source": f"vendor:{vendor.id}", "snippet": vendor.name}] + [
        {
            "source": f"contract:{c.contract_number}",
            "snippet": c.title,
        }
        for c in contracts[:3]
    ]

    return EntityResult(
        response="\n".join(lines),
        citations=citations,
        evidence=[
            {
                "source": f"vendor:{vendor.id}",
                "content": "\n".join(lines),
                "metadata": {},
            }
        ],
    )


async def _lookup_by_type(entity_type: str, entity_id: str | None, entity_name: str | None) -> EntityResult | None:
    if entity_type == "invoice" and entity_id:
        return await _invoice_lookup(entity_id)
    if entity_type == "purchase_order" and entity_id:
        return await _po_lookup(entity_id)
    if entity_type == "contract" and entity_id:
        return await _contract_lookup(entity_id)
    if entity_type == "payment" and entity_id:
        return await _payment_lookup(entity_id)
    if entity_type == "approval" and entity_id:
        return await _approval_lookup(entity_id)
    if entity_type == "vendor" and entity_name:
        return await _vendor_lookup(entity_name)
    return None


async def lookup_entity(state: dict, question: str) -> EntityResult | None:
    """Resolve a referenced entity and return an evidence-backed answer."""
    planned = state.get("planned_route") or {}
    last_invoice = state.get("last_invoice_number")

    # Planner-provided entity or follow-up reference
    if planned:
        entity_type = planned.get("entity_type")
        entity_id = planned.get("entity_id")
        entity_name = planned.get("entity_name")

        if planned.get("follow_up") and last_invoice and entity_type in (None, "invoice"):
            result = await _invoice_lookup(last_invoice)
            if result:
                result.response = f"(Continuing with invoice {last_invoice})\n\n" + result.response
            return result

        if entity_type:
            result = await _lookup_by_type(entity_type, entity_id, entity_name)
            if result:
                return result
            if entity_id:
                return EntityResult(
                    response=f"I couldn't find a {entity_type.replace('_', ' ')} with reference {entity_id}.",
                )

    reference = extract_entity_reference(question)

    if reference:
        kind, value = reference
        result = await _lookup_by_type(kind, value, None)
        if result:
            return result

    # Follow-up references to the previous invoice ("what about its payment?")
    if last_invoice and FOLLOW_UP.search(question):
        result = await _invoice_lookup(last_invoice)
        if result:
            result.response = f"(Continuing with invoice {last_invoice})\n\n" + result.response
        return result

    vendor_name = extract_vendor_name(question)
    if vendor_name:
        return await _vendor_lookup(vendor_name)

    # Missing identifiers are handled by the dedicated clarification node.
    return None
