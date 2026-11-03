"""Document generator for synthetic procurement documents."""

import logging

logger = logging.getLogger(__name__)


def generate_contract_document(contract: dict, buyer: dict, vendor: dict) -> str:
    """Generate a contract document from structured data."""
    return f"""CONTRACT AGREEMENT

Contract Number: {contract.get("contract_number", "N/A")}
Title: {contract.get("title", "N/A")}

PARTIES:
Buyer: {buyer.get("name", "N/A")}
Supplier: {vendor.get("name", "N/A")}

TERMS:
1. Contract Value: {contract.get("currency", "GBP")} {contract.get("max_value", 0):,.2f}
2. Duration: {contract.get("start_date", "N/A")} to {contract.get("end_date", "N/A")}
3. Payment Terms: Net-30
4. Status: {contract.get("status", "N/A")}
"""


def generate_invoice_document(invoice: dict, po: dict, vendor: dict) -> str:
    """Generate an invoice document from structured data."""
    return f"""INVOICE

Invoice Number: {invoice.get("invoice_number", "N/A")}
Date: {invoice.get("invoice_date", "N/A")}
Due Date: {invoice.get("due_date", "N/A")}

Vendor: {vendor.get("name", "N/A")}
PO Reference: {po.get("po_number", "N/A")}

Amount: {invoice.get("currency", "GBP")} {invoice.get("amount", 0):,.2f}
Status: {invoice.get("status", "N/A")}
Payment Status: {invoice.get("payment_status", "N/A")}
"""


def generate_po_document(po: dict, vendor: dict, department: dict) -> str:
    """Generate a purchase order document from structured data."""
    return f"""PURCHASE ORDER

PO Number: {po.get("po_number", "N/A")}
Date: {po.get("order_date", "N/A")}

Department: {department.get("name", "N/A")}
Vendor: {vendor.get("name", "N/A")}

Total Amount: {po.get("currency", "GBP")} {po.get("total_amount", 0):,.2f}
Status: {po.get("status", "N/A")}
"""
