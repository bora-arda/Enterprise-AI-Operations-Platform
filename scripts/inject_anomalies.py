#!/usr/bin/env python3
"""
Inject controlled anomalies into synthetic data.

Each anomaly is recorded with known ground truth for evaluation.
Anomaly types:
- Invoice amount exceeds PO amount
- Invoice amount exceeds contract limit
- Duplicate invoice
- Missing approval
- Expired contract
- Wrong vendor
- Already-paid invoice
- Invalid PO reference
- Wrong currency
- Payment mismatch
"""

import argparse
import copy
import json
import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

ANOMALY_TYPES = [
    "invoice_exceeds_po",
    "invoice_exceeds_contract",
    "duplicate_invoice",
    "missing_approval",
    "expired_contract",
    "wrong_vendor",
    "already_paid",
    "invalid_po",
    "wrong_currency",
    "payment_mismatch",
]

SEVERITY_MAP = {
    "invoice_exceeds_po": "high",
    "invoice_exceeds_contract": "high",
    "duplicate_invoice": "high",
    "missing_approval": "high",
    "expired_contract": "medium",
    "wrong_vendor": "high",
    "already_paid": "high",
    "invalid_po": "high",
    "wrong_currency": "medium",
    "payment_mismatch": "high",
}


def _sync_payments(invoice_id: str, amount: float, payments: list[dict]) -> None:
    """Keep existing payments consistent when an invoice amount is changed."""
    for payment in payments:
        if payment.get("invoice_id") == invoice_id:
            payment["amount"] = amount


def inject_invoice_exceeds_po(invoices: list[dict], pos: dict, payments: list[dict], count: int) -> list[dict]:
    """Make invoice amount exceed PO amount."""
    anomalies = []
    candidates = [inv for inv in invoices if inv.get("po_id") and inv["po_id"] in pos]
    selected = random.sample(candidates, min(count, len(candidates)))

    for inv in selected:
        po = pos[inv["po_id"]]
        original_amount = inv["amount"]
        inv["amount"] = round(po["total_amount"] * random.uniform(1.1, 1.5), 2)
        _sync_payments(inv["id"], inv["amount"], payments)
        anomalies.append(
            {
                "anomaly_type": "invoice_exceeds_po",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["invoice_exceeds_po"],
                "description": f"Invoice amount ({inv['amount']}) exceeds PO amount ({po['total_amount']})",
                "expected": "invoice.amount > po.total_amount",
                "original_amount": original_amount,
                "modified_amount": inv["amount"],
                "po_id": po["id"],
                "po_amount": po["total_amount"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_invoice_exceeds_contract(
    invoices: list[dict], pos: dict, contracts: dict, payments: list[dict], count: int
) -> list[dict]:
    """Make invoice amount exceed contract limit."""
    anomalies = []
    candidates = []
    for inv in invoices:
        po = pos.get(inv.get("po_id"))
        if po:
            contract = contracts.get(po.get("contract_id"))
            if contract and contract.get("max_value"):
                candidates.append((inv, contract))

    selected = random.sample(candidates, min(count, len(candidates)))

    for inv, contract in selected:
        original_amount = inv["amount"]
        inv["amount"] = round(contract["max_value"] * random.uniform(1.1, 1.5), 2)
        _sync_payments(inv["id"], inv["amount"], payments)
        anomalies.append(
            {
                "anomaly_type": "invoice_exceeds_contract",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["invoice_exceeds_contract"],
                "description": f"Invoice amount ({inv['amount']}) exceeds contract max ({contract['max_value']})",
                "expected": "invoice.amount > contract.max_value",
                "original_amount": original_amount,
                "modified_amount": inv["amount"],
                "contract_id": contract["id"],
                "contract_max": contract["max_value"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_duplicate_invoices(invoices: list[dict], count: int, exclude_ids: set[str] | None = None) -> list[dict]:
    """Create duplicate invoices."""
    anomalies = []
    exclude_ids = exclude_ids or set()
    candidates = [inv for inv in invoices if inv.get("status") != "paid" and inv["id"] not in exclude_ids]
    selected = random.sample(candidates, min(count, len(candidates)))

    for inv in selected:
        # Create a duplicate with slight variation
        duplicate = copy.deepcopy(inv)
        duplicate["id"] = f"DUP-{inv['id'][:8]}"
        duplicate["invoice_number"] = f"{inv['invoice_number']}-DUP"
        duplicate["invoice_date"] = (
            datetime.fromisoformat(inv["invoice_date"]) + timedelta(days=random.randint(1, 7))
        ).isoformat()
        invoices.append(duplicate)

        anomalies.append(
            {
                "anomaly_type": "duplicate_invoice",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "duplicate_id": duplicate["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["duplicate_invoice"],
                "description": f"Duplicate invoice detected: {inv['invoice_number']} and {duplicate['invoice_number']}",
                "expected": "same vendor, amount, and similar date",
                "original_invoice_id": inv["id"],
                "duplicate_invoice_id": duplicate["id"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_missing_approval(invoices: list[dict], approvals: list[dict], count: int) -> list[dict]:
    """Remove required approvals from invoices."""
    anomalies = []
    candidates = [inv for inv in invoices if inv.get("amount", 0) > 10000]
    selected = random.sample(candidates, min(count, len(candidates)))

    for inv in selected:
        # Remove any approval tied to this invoice
        approvals[:] = [a for a in approvals if a.get("invoice_id") != inv["id"]]
        anomalies.append(
            {
                "anomaly_type": "missing_approval",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["missing_approval"],
                "description": f"Invoice {inv['invoice_number']} (amount: {inv['amount']}) is missing required approval",
                "expected": "approval request should exist for invoices > 10000",
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_expired_contract(invoices: list[dict], pos: dict, contracts: dict, count: int) -> list[dict]:
    """Create invoices for expired contracts."""
    anomalies = []
    expired_contracts = {c["id"]: c for c in contracts.values() if c.get("end_date") and c["end_date"] < "2025-06-01"}

    if not expired_contracts:
        return anomalies

    # Build index: contract_id -> list of invoices
    invoices_by_contract = defaultdict(list)
    for inv in invoices:
        po = pos.get(inv.get("po_id"))
        if po:
            contract_id = po.get("contract_id")
            if contract_id in expired_contracts:
                invoices_by_contract[contract_id].append(inv)

    candidates = []
    for contract_id, contract_invoices in invoices_by_contract.items():
        contract = expired_contracts[contract_id]
        for inv in contract_invoices:
            candidates.append((inv, contract))

    selected = random.sample(candidates, min(count, len(candidates)))

    for inv, contract in selected:
        # Move the invoice past the contract end so the violation is detectable
        try:
            end = datetime.fromisoformat(contract["end_date"]).date()
            new_date = end + timedelta(days=random.randint(1, 45))
            inv["invoice_date"] = new_date.isoformat()
            inv["due_date"] = (new_date + timedelta(days=30)).isoformat()
        except (ValueError, TypeError):
            continue

        anomalies.append(
            {
                "anomaly_type": "expired_contract",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["expired_contract"],
                "description": f"Invoice references expired contract (ended {contract['end_date']})",
                "expected": "invoice.invoice_date > contract.end_date",
                "contract_id": contract["id"],
                "contract_end_date": contract["end_date"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_wrong_vendor(invoices: list[dict], pos: dict, vendors: list[dict], count: int) -> list[dict]:
    """Change invoice vendor to mismatch PO vendor."""
    anomalies = []
    candidates = [inv for inv in invoices if inv.get("po_id") in pos]
    selected = random.sample(candidates, min(count, len(candidates)))

    for inv in selected:
        po = pos[inv["po_id"]]
        other_vendors = [v for v in vendors if v["id"] != po["vendor_id"]]
        if not other_vendors:
            continue

        wrong_vendor = random.choice(other_vendors)
        original_vendor = inv["vendor_id"]
        inv["vendor_id"] = wrong_vendor["id"]

        anomalies.append(
            {
                "anomaly_type": "wrong_vendor",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["wrong_vendor"],
                "description": f"Invoice vendor ({wrong_vendor['id']}) does not match PO vendor ({po['vendor_id']})",
                "expected": "invoice.vendor_id != po.vendor_id",
                "original_vendor_id": original_vendor,
                "wrong_vendor_id": wrong_vendor["id"],
                "po_id": po["id"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_already_paid(invoices: list[dict], payments: list[dict], count: int) -> list[dict]:
    """Add a second payment to invoices that are already paid."""
    anomalies = []
    paid_ids = {p["invoice_id"] for p in payments if p.get("status") == "completed"}
    candidates = [inv for inv in invoices if inv["id"] in paid_ids]
    selected = random.sample(candidates, min(count, len(candidates)))

    for inv in selected:
        # Create a duplicate (second) payment for an already-paid invoice
        payment = {
            "id": f"PAY-ANOM-{inv['id'][:8]}",
            "payment_reference": f"PAY-DUP-{inv['invoice_number']}",
            "invoice_id": inv["id"],
            "amount": inv["amount"],
            "currency": inv["currency"],
            "payment_date": inv.get("due_date", "2025-06-01"),
            "method": "bank_transfer",
            "status": "completed",
        }
        payments.append(payment)

        anomalies.append(
            {
                "anomaly_type": "already_paid",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["already_paid"],
                "description": "Payment created for invoice that may already be paid",
                "expected": "payment exists for invoice with no prior payment",
                "payment_id": payment["id"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_invalid_po(invoices: list[dict], count: int) -> list[dict]:
    """Make invoices reference non-existent POs."""
    anomalies = []
    candidates = random.sample(invoices, min(count, len(invoices)))

    for inv in candidates:
        original_po = inv["po_id"]
        inv["po_id"] = f"INVALID-PO-{inv['id'][:8]}"

        anomalies.append(
            {
                "anomaly_type": "invalid_po",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["invalid_po"],
                "description": f"Invoice references non-existent PO: {inv['po_id']}",
                "expected": "po_id does not exist in purchase_orders",
                "original_po_id": original_po,
                "invalid_po_id": inv["po_id"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_wrong_currency(invoices: list[dict], pos: dict, count: int) -> list[dict]:
    """Change invoice currency to mismatch PO currency."""
    anomalies = []
    candidates = [inv for inv in invoices if inv.get("po_id") in pos]
    selected = random.sample(candidates, min(count, len(candidates)))

    for inv in selected:
        po = pos[inv["po_id"]]
        original_currency = inv["currency"]
        other_currencies = [c for c in ["GBP", "EUR", "USD"] if c != po["currency"]]
        inv["currency"] = random.choice(other_currencies)

        anomalies.append(
            {
                "anomaly_type": "wrong_currency",
                "entity_type": "invoice",
                "entity_id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "severity": SEVERITY_MAP["wrong_currency"],
                "description": f"Invoice currency ({inv['currency']}) does not match PO currency ({po['currency']})",
                "expected": "invoice.currency != po.currency",
                "original_currency": original_currency,
                "wrong_currency": inv["currency"],
                "po_currency": po["currency"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def inject_payment_mismatch(invoices: list[dict], payments: list[dict], count: int) -> list[dict]:
    """Create payments that don't match invoice amounts."""
    anomalies = []
    invoice_dict = {inv["id"]: inv for inv in invoices}
    candidates = [p for p in payments if p["invoice_id"] in invoice_dict]
    selected = random.sample(candidates, min(count, len(candidates)))

    for payment in selected:
        inv = invoice_dict[payment["invoice_id"]]
        original_amount = payment["amount"]
        payment["amount"] = round(inv["amount"] * random.uniform(0.5, 0.9), 2)

        anomalies.append(
            {
                "anomaly_type": "payment_mismatch",
                "entity_type": "payment",
                "entity_id": payment["id"],
                "payment_reference": payment["payment_reference"],
                "severity": SEVERITY_MAP["payment_mismatch"],
                "description": f"Payment amount ({payment['amount']}) does not match invoice amount ({inv['amount']})",
                "expected": "payment.amount != invoice.amount",
                "original_amount": original_amount,
                "modified_amount": payment["amount"],
                "invoice_id": inv["id"],
                "invoice_amount": inv["amount"],
                "injected_at": datetime.now().isoformat(),
            }
        )

    return anomalies


def main():
    parser = argparse.ArgumentParser(description="Inject controlled anomalies")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/synthetic"),
        help="Input directory with synthetic data",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation"),
        help="Output directory for ground truth",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--limit", type=int, default=None, help="Limit invoices for testing")
    args = parser.parse_args()

    random.seed(args.seed)

    # Load data
    def load_json(name: str, base: Path = None) -> list[dict]:
        base = base or args.input
        path = base / f"{name}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    processed = args.input.parent / "processed"
    invoices = load_json("invoices")
    pos = load_json("purchase_orders")
    payments = load_json("payments")
    approvals = load_json("approvals")
    contracts_list = load_json("contracts", processed)
    vendors_list = load_json("vendors", processed)

    pos_dict = {p["id"]: p for p in pos}
    contracts_dict = {c["id"]: c for c in contracts_list}

    if args.limit:
        invoices = invoices[: args.limit]
        logger.info(f"Limited to {len(invoices):,} invoices")

    all_anomalies = []

    logger.info("Injecting anomalies...")

    all_anomalies.extend(inject_invoice_exceeds_po(invoices, pos_dict, payments, 30))
    logger.info(f"  invoice_exceeds_po: {len(all_anomalies)}")

    all_anomalies.extend(inject_invoice_exceeds_contract(invoices, pos_dict, contracts_dict, payments, 20))
    logger.info(f"  invoice_exceeds_contract: {len(all_anomalies)}")

    flagged_ids = {a["entity_id"] for a in all_anomalies if a.get("entity_type") == "invoice"}
    all_anomalies.extend(inject_duplicate_invoices(invoices, 15, exclude_ids=flagged_ids))
    logger.info(f"  duplicate_invoice: {len(all_anomalies)}")

    all_anomalies.extend(inject_missing_approval(invoices, approvals, 25))
    logger.info(f"  missing_approval: {len(all_anomalies)}")

    all_anomalies.extend(inject_expired_contract(invoices, pos_dict, contracts_dict, 10))
    logger.info(f"  expired_contract: {len(all_anomalies)}")

    all_anomalies.extend(inject_wrong_vendor(invoices, pos_dict, vendors_list, 10))
    logger.info(f"  wrong_vendor: {len(all_anomalies)}")

    all_anomalies.extend(inject_already_paid(invoices, payments, 10))
    logger.info(f"  already_paid: {len(all_anomalies)}")

    all_anomalies.extend(inject_invalid_po(invoices, 10))
    logger.info(f"  invalid_po: {len(all_anomalies)}")

    all_anomalies.extend(inject_wrong_currency(invoices, pos_dict, 10))
    logger.info(f"  wrong_currency: {len(all_anomalies)}")

    all_anomalies.extend(inject_payment_mismatch(invoices, payments, 10))
    logger.info(f"  payment_mismatch: {len(all_anomalies)}")

    # Save ground truth
    args.output.mkdir(parents=True, exist_ok=True)
    ground_truth_path = args.output / "anomaly_ground_truth.json"
    with open(ground_truth_path, "w", encoding="utf-8") as f:
        json.dump(all_anomalies, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"\nTotal anomalies injected: {len(all_anomalies)}")
    logger.info(f"Ground truth saved to: {ground_truth_path}")

    # Save modified data back
    for name, data in [
        ("invoices", invoices),
        ("payments", payments),
        ("approvals", approvals),
    ]:
        output_path = args.input / f"{name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Updated {name}: {len(data):,} records")


if __name__ == "__main__":
    main()
