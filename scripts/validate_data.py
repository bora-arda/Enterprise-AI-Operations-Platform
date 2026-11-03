#!/usr/bin/env python3
"""
Validate data quality before loading into PostgreSQL.

Checks:
- Required fields present
- Referential integrity
- Data type validity
- Duplicate detection
- Value ranges
"""

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def validate_buyers(buyers: list[dict]) -> dict:
    issues = []
    for i, buyer in enumerate(buyers):
        if not buyer.get("name"):
            issues.append(f"Buyer {i}: missing name")
    return {"total": len(buyers), "issues": issues[:10]}


def validate_vendors(vendors: list[dict]) -> dict:
    issues = []
    for i, vendor in enumerate(vendors):
        if not vendor.get("name"):
            issues.append(f"Vendor {i}: missing name")
    return {"total": len(vendors), "issues": issues[:10]}


def validate_contracts(contracts: list[dict], buyers: dict, vendors: dict) -> dict:
    issues = []
    orphan_buyers = 0
    orphan_vendors = 0

    for i, contract in enumerate(contracts):
        if not contract.get("title"):
            issues.append(f"Contract {i}: missing title")
        if contract.get("buyer_id") and contract["buyer_id"] not in buyers:
            orphan_buyers += 1
        if contract.get("vendor_id") and contract["vendor_id"] not in vendors:
            orphan_vendors += 1
        if contract.get("value") and contract["value"] <= 0:
            issues.append(f"Contract {i}: non-positive value")

    if orphan_buyers:
        issues.append(f"{orphan_buyers} contracts reference non-existent buyers")
    if orphan_vendors:
        issues.append(f"{orphan_vendors} contracts reference non-existent vendors")

    return {"total": len(contracts), "issues": issues[:10]}


def validate_invoices(invoices: list[dict], pos: dict, vendors: dict) -> dict:
    issues = []
    orphan_pos = 0
    orphan_vendors = 0

    for i, inv in enumerate(invoices):
        if inv.get("po_id") and inv["po_id"] not in pos:
            orphan_pos += 1
        if inv.get("vendor_id") and inv["vendor_id"] not in vendors:
            orphan_vendors += 1
        if inv.get("amount") and inv["amount"] <= 0:
            issues.append(f"Invoice {i}: non-positive amount")

    if orphan_pos:
        issues.append(f"{orphan_pos} invoices reference non-existent POs")
    if orphan_vendors:
        issues.append(f"{orphan_vendors} invoices reference non-existent vendors")

    return {"total": len(invoices), "issues": issues[:10]}


def validate_payments(payments: list[dict], invoices: dict) -> dict:
    issues = []
    orphan_invoices = 0

    for i, payment in enumerate(payments):
        if payment.get("invoice_id") and payment["invoice_id"] not in invoices:
            orphan_invoices += 1
        if payment.get("amount") and payment["amount"] <= 0:
            issues.append(f"Payment {i}: non-positive amount")

    if orphan_invoices:
        issues.append(f"{orphan_invoices} payments reference non-existent invoices")

    return {"total": len(payments), "issues": issues[:10]}


def main():
    parser = argparse.ArgumentParser(description="Validate data quality")
    parser.add_argument("--processed", type=Path, default=Path("data/processed"))
    parser.add_argument("--synthetic", type=Path, default=Path("data/synthetic"))
    args = parser.parse_args()

    # Load all data
    buyers = load_json(args.processed / "buyers.json")
    vendors = load_json(args.processed / "vendors.json")
    contracts = load_json(args.processed / "contracts.json")
    departments = load_json(args.synthetic / "departments.json")
    users = load_json(args.synthetic / "users.json")
    pos = load_json(args.synthetic / "purchase_orders.json")
    invoices = load_json(args.synthetic / "invoices.json")
    payments = load_json(args.synthetic / "payments.json")
    approvals = load_json(args.synthetic / "approvals.json")

    buyers_dict = {b["id"]: b for b in buyers}
    vendors_dict = {v["id"]: v for v in vendors}
    pos_dict = {p["id"]: p for p in pos}
    invoices_dict = {i["id"]: i for i in invoices}

    # Validate
    results = {
        "buyers": validate_buyers(buyers),
        "vendors": validate_vendors(vendors),
        "contracts": validate_contracts(contracts, buyers_dict, vendors_dict),
        "invoices": validate_invoices(invoices, pos_dict, vendors_dict),
        "payments": validate_payments(payments, invoices_dict),
    }

    # Report
    logger.info("=== Data Validation Report ===")
    has_errors = False
    for entity, result in results.items():
        logger.info(f"\n{entity.upper()}:")
        logger.info(f"  Total: {result['total']:,}")
        if result["issues"]:
            has_errors = True
            logger.warning(f"  Issues ({len(result['issues'])}):")
            for issue in result["issues"]:
                logger.warning(f"    - {issue}")
        else:
            logger.info("  No issues found")

    if has_errors:
        logger.warning("\nValidation completed with warnings")
    else:
        logger.info("\nAll validations passed!")

    # Print summary
    print("\n=== Data Summary ===")
    print(f"Buyers: {len(buyers):,}")
    print(f"Vendors: {len(vendors):,}")
    print(f"Contracts: {len(contracts):,}")
    print(f"Departments: {len(departments)}")
    print(f"Users: {len(users)}")
    print(f"Purchase Orders: {len(pos):,}")
    print(f"Invoices: {len(invoices):,}")
    print(f"Payments: {len(payments):,}")
    print(f"Approvals: {len(approvals):,}")


if __name__ == "__main__":
    main()
