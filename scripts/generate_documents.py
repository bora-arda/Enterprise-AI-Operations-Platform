#!/usr/bin/env python3
"""
Generate synthetic documents from structured data.

Creates:
- Contract documents (text-based, matching database values)
- Procurement policies
- Approval policies
- Payment policies
- Invoice documents
- Purchase order documents
- Email threads
- Operational notes

All documents are generated from the structured database records to ensure
internal consistency.
"""

import argparse
import json
import logging
import random
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Document templates
CONTRACT_TEMPLATE = """CONTRACT AGREEMENT

Contract Number: {contract_number}
Title: {title}
Date: {start_date}

PARTIES:
Buyer: {buyer_name}
Supplier: {vendor_name}

TERMS:
1. Scope of Work
The Supplier agrees to deliver the following goods/services:
{line_items}

2. Contract Value
The total value of this agreement shall not exceed {currency} {max_value:,.2f}.

3. Payment Terms
Payment terms are Net-30 from invoice date. Invoices must be submitted
within 30 days of delivery.

4. Duration
This contract is effective from {start_date} to {end_date}.

5. Compliance
The Supplier must comply with all applicable laws and regulations,
including procurement policies and data protection requirements.

6. Termination
Either party may terminate this contract with 30 days written notice.

Signed: ___________________    Date: ___________
Signed: ___________________    Date: ___________
"""

INVOICE_TEMPLATE = """INVOICE

Invoice Number: {invoice_number}
Date: {invoice_date}
Due Date: {due_date}

Bill To: {buyer_name}
From: {vendor_name}

Purchase Order Reference: {po_number}

Items:
{line_items}

Total Amount: {currency} {amount:,.2f}

Payment Terms: Net-30
Payment Method: Bank Transfer

Please remit payment to:
Account Name: {vendor_name}
Bank: Example Bank
Account Number: 12345678
Sort Code: 12-34-56
"""

PO_TEMPLATE = """PURCHASE ORDER

PO Number: {po_number}
Date: {order_date}
Delivery Date: {delivery_date}

Department: {department_name}
Vendor: {vendor_name}
Contract Reference: {contract_number}

Items:
{line_items}

Total Amount: {currency} {total_amount:,.2f}

Approval Status: {status}

Requested by: {requested_by}
Approved by: {approved_by}
"""

EMAIL_TEMPLATE = """From: {sender}
To: {recipient}
Date: {date}
Subject: {subject}

{body}

---
This email thread contains {message_count} messages.
"""

POLICY_TEMPLATE = """{title}

Effective Date: {effective_date}
Version: {version}

1. Purpose
{purpose}

2. Scope
{scope}

3. Policy Details
{policy_body}

4. Compliance Requirements
{compliance}

5. Exceptions
Exceptions to this policy must be approved by {approver_role}.

6. Review
This policy is reviewed annually and updated as needed.
"""


def format_currency(amount: float, currency: str) -> str:
    """Format amount with currency."""
    return f"{currency} {amount:,.2f}"


def generate_contract_documents(contracts: list[dict], buyers: dict, vendors: dict) -> list[dict]:
    """Generate contract documents from contract records."""
    docs = []
    for contract in contracts:
        buyer = buyers.get(contract.get("buyer_id"), {})
        vendor = vendors.get(contract.get("vendor_id"), {})

        line_items = (
            "\n".join(
                f"  - {item['description']}: {item['quantity']} x {item['unit_price']} = {item['total_price']}"
                for item in contract.get("items", [])
            )
            or "  - Services as described"
        )

        max_value = contract.get("max_value") or 0
        content = CONTRACT_TEMPLATE.format(
            contract_number=contract.get("contract_number", "N/A"),
            title=contract.get("title", "N/A"),
            start_date=contract.get("start_date", "N/A"),
            buyer_name=buyer.get("name", "N/A"),
            vendor_name=vendor.get("name", "N/A"),
            line_items=line_items,
            currency=contract.get("currency", "GBP"),
            max_value=max_value,
            end_date=contract.get("end_date", "N/A"),
        )

        docs.append(
            {
                "id": f"DOC-CONT-{contract['id'][:8]}",
                "document_type": "contract",
                "title": f"Contract: {contract.get('title', 'N/A')}",
                "content": content,
                "vendor_id": contract.get("vendor_id"),
                "contract_id": contract["id"],
                "department": None,
                "effective_date": contract.get("start_date"),
                "expiration_date": contract.get("end_date"),
                "source": "synthetic",
                "metadata": {
                    "contract_number": contract.get("contract_number"),
                    "buyer_name": buyer.get("name"),
                    "vendor_name": vendor.get("name"),
                },
            }
        )

    return docs


def generate_invoice_documents(invoices: list[dict], pos: dict, vendors: dict) -> list[dict]:
    """Generate invoice documents from invoice records."""
    docs = []
    for inv in invoices:
        vendor = vendors.get(inv.get("vendor_id"), {})
        po = pos.get(inv.get("po_id"), {})

        line_items = (
            "\n".join(
                f"  {i + 1}. {item['description']}: {item['quantity']} x {item['unit_price']} = {item['total_price']}"
                for i, item in enumerate(inv.get("items", []))
            )
            or "  1. Services rendered"
        )

        content = INVOICE_TEMPLATE.format(
            invoice_number=inv.get("invoice_number", "N/A"),
            invoice_date=inv.get("invoice_date", "N/A"),
            due_date=inv.get("due_date", "N/A"),
            buyer_name="Procurement Department",
            vendor_name=vendor.get("name", "N/A"),
            po_number=po.get("po_number", "N/A"),
            line_items=line_items,
            currency=inv.get("currency", "GBP"),
            amount=inv.get("amount") or 0,
        )

        docs.append(
            {
                "id": f"DOC-INV-{inv['id'][:8]}",
                "document_type": "invoice",
                "title": f"Invoice: {inv.get('invoice_number', 'N/A')}",
                "content": content,
                "vendor_id": inv.get("vendor_id"),
                "invoice_id": inv["id"],
                "department": None,
                "effective_date": inv.get("invoice_date"),
                "expiration_date": inv.get("due_date"),
                "source": "synthetic",
                "metadata": {
                    "invoice_number": inv.get("invoice_number"),
                    "amount": inv.get("amount"),
                    "currency": inv.get("currency"),
                },
            }
        )

    return docs


def generate_purchase_order_documents(pos: list[dict], vendors: dict, departments: dict) -> list[dict]:
    """Generate purchase order documents from PO records."""
    docs = []
    for po in pos:
        vendor = vendors.get(po.get("vendor_id"), {})
        dept = departments.get(po.get("department_id"), {})

        line_items = (
            "\n".join(
                f"  {i + 1}. {item['description']}: {item['quantity']} x {item['unit_price']} = {item['total_price']}"
                for i, item in enumerate(po.get("items", []))
            )
            or "  1. Services as described"
        )

        content = PO_TEMPLATE.format(
            po_number=po.get("po_number", "N/A"),
            order_date=po.get("order_date", "N/A"),
            delivery_date=po.get("delivery_date", "N/A"),
            department_name=dept.get("name", "N/A"),
            vendor_name=vendor.get("name", "N/A"),
            contract_number="N/A",
            line_items=line_items,
            currency=po.get("currency", "GBP"),
            total_amount=po.get("total_amount") or 0,
            status=po.get("status", "N/A"),
            requested_by="System",
            approved_by="System",
        )

        docs.append(
            {
                "id": f"DOC-PO-{po['id'][:8]}",
                "document_type": "purchase_order",
                "title": f"PO: {po.get('po_number', 'N/A')}",
                "content": content,
                "vendor_id": po.get("vendor_id"),
                "po_id": po["id"],
                "department": dept.get("code"),
                "effective_date": po.get("order_date"),
                "expiration_date": po.get("delivery_date"),
                "source": "synthetic",
                "metadata": {
                    "po_number": po.get("po_number"),
                    "department": dept.get("code"),
                },
            }
        )

    return docs


def generate_policy_documents() -> list[dict]:
    """Generate standard policy documents."""
    policies = [
        {
            "id": "DOC-POL-PROC-001",
            "document_type": "policy",
            "title": "Procurement Policy",
            "content": POLICY_TEMPLATE.format(
                title="Procurement Policy",
                effective_date="2025-01-01",
                version="2.0",
                purpose="This policy establishes the rules and procedures for procurement activities to ensure value for money, transparency, and compliance.",
                scope="This policy applies to all departments and staff involved in procurement activities.",
                policy_body="""All purchases must follow these guidelines:
1. Purchases under GBP 5,000: Single quote required
2. Purchases GBP 5,000 - GBP 25,000: Three quotes required
3. Purchases over GBP 25,000: Competitive tender required
4. All contracts must be reviewed by Legal before signing
5. No purchases from blacklisted vendors
6. All POs require manager approval""",
                compliance="Non-compliance may result in disciplinary action. All procurement decisions must be documented.",
                approver_role="Procurement Manager",
            ),
            "department": None,
            "effective_date": "2025-01-01",
            "source": "synthetic",
            "metadata": {"policy_type": "procurement"},
        },
        {
            "id": "DOC-POL-APPR-001",
            "document_type": "policy",
            "title": "Approval Policy",
            "content": POLICY_TEMPLATE.format(
                title="Approval Policy",
                effective_date="2025-01-01",
                version="1.5",
                purpose="This policy defines the approval requirements for various business operations.",
                scope="This policy applies to all approval workflows in the system.",
                policy_body="""Approval requirements:
1. Invoices under GBP 10,000: Manager approval required
2. Invoices GBP 10,000 - GBP 50,000: Manager + Finance approval required
3. Invoices over GBP 50,000: Director + Finance approval required
4. All approvals must be documented with justification
5. Approval timeout: 48 hours (escalation to next level)""",
                compliance="All approvals must be recorded in the system with timestamp and justification.",
                approver_role="Department Director",
            ),
            "department": None,
            "effective_date": "2025-01-01",
            "source": "synthetic",
            "metadata": {"policy_type": "approval"},
        },
        {
            "id": "DOC-POL-PAY-001",
            "document_type": "policy",
            "title": "Payment Policy",
            "content": POLICY_TEMPLATE.format(
                title="Payment Policy",
                effective_date="2025-01-01",
                version="1.0",
                purpose="This policy defines payment terms and procedures.",
                scope="This policy applies to all payment operations.",
                policy_body="""Payment procedures:
1. Standard payment terms: Net-30 from invoice date
2. Early payment discounts must be documented
3. All payments require matching invoice and PO
4. Duplicate payments must be flagged and investigated
5. Payment references must be unique
6. Refunds require manager approval""",
                compliance="All payments must be reconciled with invoices monthly.",
                approver_role="Finance Manager",
            ),
            "department": None,
            "effective_date": "2025-01-01",
            "source": "synthetic",
            "metadata": {"policy_type": "payment"},
        },
        {
            "id": "DOC-POL-VEND-001",
            "document_type": "policy",
            "title": "Vendor Management Policy",
            "content": POLICY_TEMPLATE.format(
                title="Vendor Management Policy",
                effective_date="2025-01-01",
                version="1.0",
                purpose="This policy defines vendor onboarding, management, and offboarding procedures.",
                scope="This policy applies to all vendor relationships.",
                policy_body="""Vendor management rules:
1. New vendors must complete due diligence check
2. Vendor performance reviewed annually
3. Blacklisted vendors must not be used
4. Vendor changes require approval
5. Vendor contracts must be on file
6. Conflicts of interest must be declared""",
                compliance="Vendor records must be maintained in the vendor management system.",
                approver_role="Procurement Director",
            ),
            "department": None,
            "effective_date": "2025-01-01",
            "source": "synthetic",
            "metadata": {"policy_type": "vendor"},
        },
    ]
    return policies


def generate_email_threads(invoices: list[dict], pos: dict, users: dict) -> list[dict]:
    """Generate synthetic email threads related to invoices."""
    docs = []
    sample_invoices = random.sample(invoices, min(100, len(invoices)))

    for inv in sample_invoices[:20]:
        po = pos.get(inv.get("po_id"), {})
        user = random.choice(list(users.values()))

        content = EMAIL_TEMPLATE.format(
            sender=user.get("email", "user@example.com"),
            recipient="procurement@example.com",
            date=inv.get("invoice_date", "2025-01-01"),
            subject=f"RE: Invoice {inv.get('invoice_number', 'N/A')}",
            body=f"""Dear Team,

I am writing regarding invoice {inv.get("invoice_number", "N/A")} for PO {po.get("po_number", "N/A")}.

Could you please confirm the status of this invoice? The invoice was submitted on {inv.get("invoice_date", "N/A")} and is due on {inv.get("due_date", "N/A")}.

Thank you,
{user.get("name", "User")}""",
            message_count=random.randint(2, 5),
        )

        docs.append(
            {
                "id": f"DOC-EMAIL-{inv['id'][:8]}",
                "document_type": "email",
                "title": f"Email: {inv.get('invoice_number', 'N/A')}",
                "content": content,
                "invoice_id": inv["id"],
                "po_id": inv.get("po_id"),
                "department": user.get("department"),
                "effective_date": inv.get("invoice_date"),
                "source": "synthetic",
                "metadata": {"email_count": random.randint(2, 5)},
            }
        )

    return docs


def generate_operational_notes(invoices: list[dict], pos: dict, payments: list[dict]) -> list[dict]:
    """Generate operational notes and comments."""
    docs = []

    for inv in invoices[:50]:
        po = pos.get(inv.get("po_id"), {})
        inv_payments = [p for p in payments if p.get("invoice_id") == inv["id"]]

        notes = []
        if inv_payments:
            notes.append(f"Payment received: {inv_payments[0].get('payment_reference', 'N/A')}")
        else:
            notes.append("Payment pending - awaiting approval")

        if inv.get("status") == "overdue":
            notes.append("URGENT: Invoice is overdue. Follow up with vendor.")

        content = f"""OPERATIONAL NOTE

Entity: Invoice {inv.get("invoice_number", "N/A")}
PO: {po.get("po_number", "N/A")}
Amount: {inv.get("currency", "GBP")} {inv.get("amount", 0):,.2f}
Status: {inv.get("status", "N/A")}

Notes:
{chr(10).join(f"- {n}" for n in notes)}

Created: {datetime.now().isoformat()}
"""

        docs.append(
            {
                "id": f"DOC-NOTE-{inv['id'][:8]}",
                "document_type": "operational_note",
                "title": f"Note: {inv.get('invoice_number', 'N/A')}",
                "content": content,
                "invoice_id": inv["id"],
                "source": "synthetic",
                "metadata": {"note_type": "operational"},
            }
        )

    return docs


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic documents")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/synthetic"),
        help="Input directory with synthetic data",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/documents"),
        help="Output directory for documents",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    # Load synthetic data
    def load_json(name: str, base: Path = None) -> list[dict]:
        base = base or args.input
        path = base / f"{name}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    processed = args.input.parent / "processed"
    contracts = load_json("contracts", processed)
    invoices = load_json("invoices")
    pos = load_json("purchase_orders")
    payments = load_json("payments")
    departments = load_json("departments")
    users = load_json("users")

    # Load buyers and vendors from processed data
    buyers_list = load_json("buyers", processed)
    vendors_list = load_json("vendors", processed)

    buyers = {b["id"]: b for b in buyers_list}
    vendors = {v["id"]: v for v in vendors_list}
    pos_dict = {p["id"]: p for p in pos}
    dept_dict = {d["id"]: d for d in departments}
    users_dict = {u["id"]: u for u in users}

    # Generate documents
    logger.info("Generating contract documents...")
    contract_docs = generate_contract_documents(contracts, buyers, vendors)

    logger.info("Generating invoice documents...")
    invoice_docs = generate_invoice_documents(invoices, pos_dict, vendors)

    logger.info("Generating purchase order documents...")
    po_docs = generate_purchase_order_documents(pos, vendors, dept_dict)

    logger.info("Generating policy documents...")
    policy_docs = generate_policy_documents()

    logger.info("Generating email threads...")
    email_docs = generate_email_threads(invoices, pos_dict, users_dict)

    logger.info("Generating operational notes...")
    note_docs = generate_operational_notes(invoices, pos_dict, payments)

    # Combine all documents
    all_docs = contract_docs + invoice_docs + po_docs + policy_docs + email_docs + note_docs

    # Save
    args.output.mkdir(parents=True, exist_ok=True)
    output_path = args.output / "documents.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Saved {len(all_docs):,} documents to {output_path}")
    logger.info(f"  Contract docs: {len(contract_docs):,}")
    logger.info(f"  Invoice docs: {len(invoice_docs):,}")
    logger.info(f"  PO docs: {len(po_docs):,}")
    logger.info(f"  Policy docs: {len(policy_docs):,}")
    logger.info(f"  Email threads: {len(email_docs):,}")
    logger.info(f"  Operational notes: {len(note_docs):,}")


if __name__ == "__main__":
    main()
