"""Investigation workflow node.

Deterministic, evidence-backed investigation across invoices, POs, contracts,
payments, and approvals. Every claim is derived from database records and
surfaced as a citation.
"""

import logging
import re
from datetime import date

from sqlalchemy import select

from procurement_ai.anomaly_detection.rules import run_all_rules
from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import (
    ApprovalRequest,
    Contract,
    Invoice,
    Payment,
    PurchaseOrder,
    Vendor,
)

logger = logging.getLogger(__name__)


def _fmt_amount(amount, currency: str | None) -> str:
    if amount is None:
        return "unknown"
    return f"{currency or ''} {float(amount):,.2f}".strip()


def _days_overdue(due_date: date | None) -> int | None:
    if not due_date:
        return None
    delta = (date.today() - due_date).days
    return delta if delta > 0 else None


async def _load_invoice_bundle(invoice_number: str) -> dict | None:
    """Load invoice and all related records."""
    async with AsyncSessionLocal() as session:
        invoice_result = await session.execute(select(Invoice).where(Invoice.invoice_number == invoice_number))
        invoice = invoice_result.scalar_one_or_none()
        if not invoice:
            return None

        po = None
        if invoice.po_id:
            po_result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == invoice.po_id))
            po = po_result.scalar_one_or_none()

        contract = None
        if po and po.contract_id:
            contract_result = await session.execute(select(Contract).where(Contract.id == po.contract_id))
            contract = contract_result.scalar_one_or_none()

        vendor = None
        if invoice.vendor_id:
            vendor_result = await session.execute(select(Vendor).where(Vendor.id == invoice.vendor_id))
            vendor = vendor_result.scalar_one_or_none()

        payment_result = await session.execute(select(Payment).where(Payment.invoice_id == invoice.id))
        payments = list(payment_result.scalars().all())

        approval_result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.invoice_id == invoice.id))
        approvals = list(approval_result.scalars().all())

        return {
            "invoice": invoice,
            "po": po,
            "contract": contract,
            "vendor": vendor,
            "payments": payments,
            "approvals": approvals,
        }


def _build_response(bundle: dict) -> tuple[str, list[dict], list[dict]]:
    """Build deterministic evidence-backed response."""
    invoice = bundle["invoice"]
    po = bundle["po"]
    contract = bundle["contract"]
    payments = bundle["payments"]
    approvals = bundle["approvals"]

    citations: list[dict] = []
    evidence: list[dict] = []
    findings: list[str] = []

    def cite(source: str, snippet: str) -> None:
        citations.append({"source": source, "snippet": snippet})
        evidence.append({"source": source, "content": snippet, "metadata": {}})

    # Core invoice facts
    cite(
        f"invoice:{invoice.invoice_number}",
        f"Amount {_fmt_amount(invoice.amount, invoice.currency)}, "
        f"issued {invoice.invoice_date}, due {invoice.due_date}, "
        f"status={invoice.status}, payment_status={invoice.payment_status}",
    )

    lines = [
        f"Invoice {invoice.invoice_number} is for {_fmt_amount(invoice.amount, invoice.currency)}, "
        f"issued on {invoice.invoice_date} and due on {invoice.due_date}."
    ]

    # PO facts
    if po:
        cite(
            f"purchase_order:{po.po_number}",
            f"PO total {_fmt_amount(po.total_amount, po.currency)}, status={po.status}",
        )
        lines.append(f"It is linked to purchase order {po.po_number} ({_fmt_amount(po.total_amount, po.currency)}).")

        if invoice.amount and po.total_amount and invoice.amount > po.total_amount:
            diff = float(invoice.amount) - float(po.total_amount)
            findings.append(f"Invoice amount exceeds the PO by {diff:,.2f} {invoice.currency or ''}".strip())
        if invoice.vendor_id != po.vendor_id:
            findings.append("Invoice vendor does not match the PO vendor")
        if invoice.currency != po.currency:
            findings.append(f"Currency mismatch: invoice {invoice.currency} vs PO {po.currency}")
    else:
        findings.append("No valid purchase order is linked to this invoice")

    # Contract facts
    if contract:
        cite(
            f"contract:{contract.contract_number}",
            f"Contract '{contract.title}', max value "
            f"{_fmt_amount(contract.max_value, contract.currency)}, "
            f"valid {contract.start_date} to {contract.end_date}",
        )
        lines.append(
            f"The contract {contract.contract_number} is valid from "
            f"{contract.start_date} to {contract.end_date} with a maximum value of "
            f"{_fmt_amount(contract.max_value, contract.currency)}."
        )

        if contract.max_value and invoice.amount and invoice.amount > contract.max_value:
            findings.append(
                f"Invoice amount exceeds the contract maximum by "
                f"{float(invoice.amount) - float(contract.max_value):,.2f} "
                f"{contract.currency or ''}".strip()
            )
        if contract.end_date and invoice.invoice_date and invoice.invoice_date > contract.end_date:
            findings.append(f"Invoice was issued after the contract expired on {contract.end_date}")

    # Payment facts
    completed = [p for p in payments if p.status == "completed"]
    if completed:
        latest = completed[-1]
        cite(
            f"payment:{latest.payment_reference}",
            f"Payment {_fmt_amount(latest.amount, latest.currency)} on {latest.payment_date}, status={latest.status}",
        )
        lines.append(
            f"A payment of {_fmt_amount(latest.amount, latest.currency)} was recorded "
            f"on {latest.payment_date} (reference {latest.payment_reference})."
        )
        if invoice.amount and latest.amount and latest.amount != invoice.amount:
            findings.append(
                f"Payment amount ({_fmt_amount(latest.amount, latest.currency)}) does not match the invoice amount"
            )
    else:
        cite("payment:none", "No completed payment found for this invoice")
        lines.append("No completed payment has been recorded for this invoice.")

    # Approval facts
    approved = [a for a in approvals if a.status == "approved"]
    if approved:
        cite(
            f"approval:{approved[-1].approval_number}",
            f"Approval status={approved[-1].status}",
        )
        lines.append(f"The invoice has an approved approval request ({approved[-1].approval_number}).")
    elif approvals:
        cite(
            f"approval:{approvals[-1].approval_number}",
            f"Approval status={approvals[-1].status}",
        )
        lines.append(f"An approval request exists with status '{approvals[-1].status}'.")
    else:
        findings.append("No approval request is recorded for this invoice")

    # Overdue reasoning
    overdue_days = _days_overdue(invoice.due_date)
    if not completed and overdue_days:
        lines.append(
            f"The invoice is {overdue_days} days past its due date and remains unpaid, "
            f"which is why it is shown as overdue."
        )
    elif completed and overdue_days:
        lines.append(
            "Although the due date has passed, a completed payment is recorded, so the "
            "invoice should not be treated as outstanding."
        )
    elif not completed:
        lines.append("The invoice is unpaid and has not yet reached its due date.")

    if findings:
        lines.append("")
        lines.append("Potential issues identified:")
        for f in findings:
            lines.append(f"- {f}")
    else:
        lines.append("")
        lines.append("No policy or consistency issues were detected for this invoice.")

    return "\n".join(lines), citations, evidence


async def investigation_workflow_node(state: dict) -> dict:
    """Investigate an invoice using real database evidence."""
    question = state.get("user_input", "")
    planned = state.get("planned_route") or {}

    invoice_number = None
    if planned.get("entity_type") == "invoice" and planned.get("entity_id"):
        invoice_number = planned["entity_id"]
    if not invoice_number:
        match = re.search(r"\b(INV-\d+)\b", question, re.IGNORECASE)
        if match:
            invoice_number = match.group(1).upper()

    if not invoice_number:
        state["response"] = (
            "I can investigate a specific invoice, but I need its invoice number "
            "(for example, INV-000001). Could you provide it?"
        )
        return state

    try:
        bundle = await _load_invoice_bundle(invoice_number)
    except Exception as e:
        logger.error(f"Investigation query failed: {e}", exc_info=True)
        state["response"] = "I encountered a database error while investigating this invoice."
        state["errors"] = state.get("errors", []) + [str(e)]
        return state

    if not bundle:
        state["response"] = f"I couldn't find an invoice with number {invoice_number}."
        return state

    response, citations, evidence = _build_response(bundle)

    # Run deterministic rules for structured findings
    invoice = bundle["invoice"]
    po = bundle["po"]
    contract = bundle["contract"]
    inv_dict = {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "amount": float(invoice.amount),
        "currency": invoice.currency,
        "vendor_id": str(invoice.vendor_id) if invoice.vendor_id else None,
        "po_id": str(invoice.po_id) if invoice.po_id else None,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
    }
    po_dict = None
    if po:
        po_dict = {
            "id": str(po.id),
            "po_number": po.po_number,
            "vendor_id": str(po.vendor_id) if po.vendor_id else None,
            "total_amount": float(po.total_amount),
            "currency": po.currency,
        }
    contract_dict = None
    if contract:
        contract_dict = {
            "id": str(contract.id),
            "max_value": float(contract.max_value) if contract.max_value else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
        }

    state["evidence"] = evidence
    state["citations"] = citations
    state["response"] = response
    state["confidence"] = 0.9 if citations else 0.4
    state["workflow"] = "investigation"
    state["last_invoice_number"] = invoice_number

    anomalies = run_all_rules(inv_dict, po_dict, contract_dict, [])
    state["tool_results"] = [{"tool_name": "run_anomaly_rules", "success": True, "result": anomalies, "error": None}]

    return state
