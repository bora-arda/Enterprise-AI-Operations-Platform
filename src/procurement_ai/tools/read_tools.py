"""Read-only tools for querying procurement data."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.database.models import Contract, Invoice, Payment, PurchaseOrder, Vendor

logger = logging.getLogger(__name__)


async def get_invoice(session: AsyncSession, invoice_id: str) -> dict | None:
    """Retrieve a single invoice by its ID or invoice number."""
    # Try by invoice_number first
    result = await session.execute(select(Invoice).where(Invoice.invoice_number == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        # Try by UUID
        try:
            result = await session.execute(select(Invoice).where(Invoice.id == UUID(invoice_id)))
            invoice = result.scalar_one_or_none()
        except ValueError:
            pass

    if not invoice:
        return None

    return {
        "invoice_id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "po_id": str(invoice.po_id) if invoice.po_id else None,
        "vendor_id": str(invoice.vendor_id) if invoice.vendor_id else None,
        "amount": float(invoice.amount),
        "currency": invoice.currency,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "status": invoice.status,
        "payment_status": invoice.payment_status,
    }


async def get_purchase_order(session: AsyncSession, po_id: str) -> dict | None:
    """Retrieve a single purchase order by its ID or PO number."""
    result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == po_id))
    po = result.scalar_one_or_none()

    if not po:
        try:
            result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == UUID(po_id)))
            po = result.scalar_one_or_none()
        except ValueError:
            pass

    if not po:
        return None

    return {
        "po_id": str(po.id),
        "po_number": po.po_number,
        "contract_id": str(po.contract_id) if po.contract_id else None,
        "vendor_id": str(po.vendor_id) if po.vendor_id else None,
        "department_id": str(po.department_id) if po.department_id else None,
        "total_amount": float(po.total_amount),
        "currency": po.currency,
        "status": po.status,
        "order_date": po.order_date.isoformat() if po.order_date else None,
        "delivery_date": po.delivery_date.isoformat() if po.delivery_date else None,
    }


async def get_contract(session: AsyncSession, contract_id: str) -> dict | None:
    """Retrieve a single contract by its ID or contract number."""
    result = await session.execute(select(Contract).where(Contract.contract_number == contract_id))
    contract = result.scalar_one_or_none()

    if not contract:
        try:
            result = await session.execute(select(Contract).where(Contract.id == UUID(contract_id)))
            contract = result.scalar_one_or_none()
        except ValueError:
            pass

    if not contract:
        return None

    return {
        "contract_id": str(contract.id),
        "contract_number": contract.contract_number,
        "title": contract.title,
        "vendor_id": str(contract.vendor_id) if contract.vendor_id else None,
        "buyer_id": str(contract.buyer_id) if contract.buyer_id else None,
        "value": float(contract.value) if contract.value else None,
        "max_value": float(contract.max_value) if contract.max_value else None,
        "currency": contract.currency,
        "start_date": contract.start_date.isoformat() if contract.start_date else None,
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "status": contract.status,
        "payment_terms": contract.payment_terms,
    }


async def get_vendor(session: AsyncSession, vendor_id: str) -> dict | None:
    """Retrieve a single vendor by its ID or name."""
    result = await session.execute(select(Vendor).where(Vendor.id == UUID(vendor_id)))
    vendor = result.scalar_one_or_none()

    if not vendor:
        try:
            result = await session.execute(select(Vendor).where(Vendor.id == UUID(vendor_id)))
            vendor = result.scalar_one_or_none()
        except ValueError:
            pass

    if not vendor:
        return None

    return {
        "vendor_id": str(vendor.id),
        "name": vendor.name,
        "country": vendor.country,
        "status": vendor.status,
    }


async def get_payment_status(session: AsyncSession, invoice_id: str) -> dict | None:
    """Check payment status for an invoice."""
    result = await session.execute(select(Payment).where(Payment.invoice_id == UUID(invoice_id)))
    payments = result.scalars().all()

    if not payments:
        return {"invoice_id": invoice_id, "payment_status": "no_payment_found", "payments": []}

    return {
        "invoice_id": invoice_id,
        "payment_status": "paid" if any(p.status == "completed" for p in payments) else "pending",
        "payments": [
            {
                "payment_id": str(p.id),
                "payment_reference": p.payment_reference,
                "amount": float(p.amount),
                "currency": p.currency,
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "status": p.status,
            }
            for p in payments
        ],
    }
