"""Deterministic anomaly detection rules."""

import logging
from datetime import date

logger = logging.getLogger(__name__)


def invoice_exceeds_po(invoice: dict, po: dict | None) -> dict | None:
    """Check if invoice amount exceeds PO amount."""
    if not po:
        return None

    inv_amount = invoice.get("amount", 0)
    po_amount = po.get("total_amount", 0)

    if inv_amount > po_amount:
        return {
            "rule": "invoice_exceeds_po",
            "severity": "high",
            "description": f"Invoice amount ({inv_amount}) exceeds PO amount ({po_amount})",
            "details": {
                "invoice_amount": inv_amount,
                "po_amount": po_amount,
                "excess": inv_amount - po_amount,
            },
        }
    return None


def invoice_exceeds_contract(invoice: dict, po: dict | None, contract: dict | None) -> dict | None:
    """Check if invoice amount exceeds contract limit."""
    if not contract:
        return None

    inv_amount = invoice.get("amount", 0)
    max_value = contract.get("max_value")

    if max_value and inv_amount > max_value:
        return {
            "rule": "invoice_exceeds_contract",
            "severity": "high",
            "description": f"Invoice amount ({inv_amount}) exceeds contract limit ({max_value})",
            "details": {
                "invoice_amount": inv_amount,
                "contract_max": max_value,
                "excess": inv_amount - max_value,
            },
        }
    return None


def missing_approval(invoice: dict, approvals: list[dict]) -> dict | None:
    """Check if invoice is missing required approval."""
    if invoice.get("amount", 0) > 10000:
        has_approval = any(
            a.get("invoice_id") == invoice.get("id") and a.get("status") == "approved" for a in approvals
        )
        if not has_approval:
            return {
                "rule": "missing_approval",
                "severity": "high",
                "description": f"Invoice {invoice.get('invoice_number')} missing required approval",
                "details": {
                    "invoice_id": invoice.get("id"),
                    "amount": invoice.get("amount"),
                },
            }
    return None


def expired_contract(invoice: dict, contract: dict | None) -> dict | None:
    """Check if invoice references an expired contract."""
    if not contract or not contract.get("end_date"):
        return None

    invoice_date = invoice.get("invoice_date")
    if not invoice_date:
        return None

    end_date = contract["end_date"]
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if isinstance(invoice_date, str):
        invoice_date = date.fromisoformat(invoice_date)

    if invoice_date > end_date:
        return {
            "rule": "expired_contract",
            "severity": "medium",
            "description": f"Invoice references expired contract (ended {end_date})",
            "details": {
                "contract_end_date": str(end_date),
                "invoice_date": str(invoice_date),
            },
        }
    return None


def wrong_vendor(invoice: dict, po: dict | None) -> dict | None:
    """Check if invoice vendor matches PO vendor."""
    if not po:
        return None

    if invoice.get("vendor_id") != po.get("vendor_id"):
        return {
            "rule": "wrong_vendor",
            "severity": "high",
            "description": "Invoice vendor does not match PO vendor",
            "details": {
                "invoice_vendor_id": invoice.get("vendor_id"),
                "po_vendor_id": po.get("vendor_id"),
            },
        }
    return None


def wrong_currency(invoice: dict, po: dict | None) -> dict | None:
    """Check if invoice currency matches PO currency."""
    if not po:
        return None

    if invoice.get("currency") != po.get("currency"):
        return {
            "rule": "wrong_currency",
            "severity": "medium",
            "description": (
                f"Invoice currency ({invoice.get('currency')}) does not match PO currency ({po.get('currency')})"
            ),
            "details": {
                "invoice_currency": invoice.get("currency"),
                "po_currency": po.get("currency"),
            },
        }
    return None


def payment_mismatch(payment: dict, invoice: dict) -> dict | None:
    """Check if payment amount matches invoice amount."""
    if payment.get("amount") != invoice.get("amount"):
        return {
            "rule": "payment_mismatch",
            "severity": "high",
            "description": (
                f"Payment amount ({payment.get('amount')}) does not match invoice amount ({invoice.get('amount')})"
            ),
            "details": {
                "payment_amount": payment.get("amount"),
                "invoice_amount": invoice.get("amount"),
            },
        }
    return None


def run_all_rules(invoice: dict, po: dict | None, contract: dict | None, approvals: list[dict]) -> list[dict]:
    """Run all deterministic rules and return anomalies."""
    anomalies = []

    checks = [
        invoice_exceeds_po(invoice, po),
        invoice_exceeds_contract(invoice, po, contract),
        missing_approval(invoice, approvals),
        expired_contract(invoice, contract),
        wrong_vendor(invoice, po),
        wrong_currency(invoice, po),
    ]

    for result in checks:
        if result:
            anomalies.append(result)

    return anomalies
