#!/usr/bin/env python3
"""
Generate deterministic synthetic enterprise data.

Builds on the public procurement backbone to create:
- Departments
- Users
- Purchase Orders (linked to public contracts)
- Invoices (linked to POs)
- Payments (linked to Invoices)
- Approval Requests (linked to Invoices)

All data is deterministic (seeded) and maintains referential integrity.
"""

import argparse
import json
import logging
import random
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
DEPARTMENTS = [
    ("IT", "Information Technology", 500000),
    ("Finance", "Finance & Accounting", 200000),
    ("HR", "Human Resources", 150000),
    ("Operations", "Operations", 300000),
    ("Marketing", "Marketing & Communications", 250000),
    ("Legal", "Legal & Compliance", 100000),
    ("Procurement", "Procurement", 100000),
    ("Facilities", "Facilities & Maintenance", 200000),
]

ROLES = ["specialist", "manager", "director", "admin"]

FIRST_NAMES = [
    "James",
    "Mary",
    "Robert",
    "Patricia",
    "John",
    "Jennifer",
    "Michael",
    "Linda",
    "David",
    "Elizabeth",
    "William",
    "Barbara",
    "Richard",
    "Susan",
    "Joseph",
    "Jessica",
    "Thomas",
    "Sarah",
    "Charles",
    "Karen",
    "Christopher",
    "Lisa",
    "Daniel",
    "Nancy",
    "Matthew",
    "Betty",
    "Anthony",
    "Margaret",
    "Mark",
    "Sandra",
    "Donald",
    "Ashley",
    "Steven",
    "Kimberly",
    "Paul",
    "Emily",
    "Andrew",
    "Donna",
    "Joshua",
    "Michelle",
    "Kenneth",
    "Carol",
    "Kevin",
    "Amanda",
    "Brian",
    "Dorothy",
    "George",
    "Melissa",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
]

CATEGORIES = [
    (
        "IT",
        "IT Equipment & Software",
        ["Laptops", "Servers", "Software Licenses", "Monitors", "Network Equipment"],
    ),
    ("Finance", "Financial Services", ["Audit Services", "Consulting", "Bookkeeping"]),
    ("HR", "HR Services", ["Recruitment", "Training", "Employee Benefits"]),
    ("Operations", "Operational Supplies", ["Office Supplies", "Safety Equipment", "Tools"]),
    ("Marketing", "Marketing Services", ["Advertising", "Design", "Event Management"]),
    ("Legal", "Legal Services", ["Contract Review", "Compliance", "Litigation"]),
    ("Facilities", "Facilities Services", ["Cleaning", "Maintenance", "Security", "Catering"]),
    ("Procurement", "Procurement Services", ["Vendor Management", "Sourcing", "Logistics"]),
]

CURRENCIES = ["GBP", "EUR", "USD"]


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_id(prefix: str, number: int) -> str:
    return f"{prefix}-{number:06d}"


def random_date(start: date, end: date) -> date:
    """Generate a random date between start and end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))


def random_amount(min_val: float, max_val: float) -> Decimal:
    """Generate a random monetary amount."""
    amount = random.uniform(min_val, max_val)
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_departments() -> list[dict]:
    """Generate department records."""
    departments = []
    for i, (code, name, budget) in enumerate(DEPARTMENTS, 1):
        departments.append(
            {
                "id": generate_uuid(),
                "name": name,
                "code": code,
                "budget_limit": budget,
                "created_at": datetime.now().isoformat(),
            }
        )
    return departments


def generate_users(departments: list[dict], num_users: int = 50) -> list[dict]:
    """Generate user records."""
    users = []
    used_emails = set()

    for i in range(num_users):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}@example.com"

        # Ensure unique emails
        while email in used_emails:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}@example.com"
        used_emails.add(email)

        dept = random.choice(departments)
        users.append(
            {
                "id": generate_uuid(),
                "name": f"{first} {last}",
                "email": email,
                "role": random.choice(ROLES),
                "department_id": dept["id"],
                "created_at": datetime.now().isoformat(),
            }
        )
    return users


def generate_purchase_orders(
    contracts: list[dict],
    departments: list[dict],
    avg_pos_per_contract: int = 3,
) -> list[dict]:
    """Generate purchase orders linked to public contracts.

    Only contracts that overlap the synthetic operating window (2024-2026)
    are eligible, so invoices can be dated inside the contract period.
    """
    pos = []
    po_counter = 1

    window_start = date(2024, 1, 1)
    window_end = date(2026, 6, 30)

    eligible = []
    for contract in contracts:
        try:
            c_start = date.fromisoformat(contract["start_date"])
            c_end = date.fromisoformat(contract["end_date"])
        except (KeyError, ValueError, TypeError):
            continue
        if c_end < window_start or c_start > window_end:
            continue
        eligible.append((contract, max(c_start, window_start), min(c_end, window_end)))

    for contract, c_start, c_end in eligible:
        num_pos = random.randint(1, avg_pos_per_contract * 2)
        for _ in range(num_pos):
            dept = random.choice(departments)
            category_info = next((c for c in CATEGORIES if c[0] == dept["code"]), CATEGORIES[0])

            order_date = random_date(c_start, c_end)
            delivery_date = order_date + timedelta(days=random.randint(7, 60))

            # PO amount stays comfortably inside the contract value
            contract_value = contract.get("value") or 0
            if not contract_value or contract_value < 2000:
                continue
            po_amount = random_amount(
                max(100, contract_value * 0.10),
                contract_value * 0.70,
            )

            po_id = generate_uuid()
            po_number = f"PO-{po_counter:06d}"
            po_counter += 1

            # Generate line items
            num_items = random.randint(1, 5)
            items = []
            remaining = float(po_amount)
            for j in range(num_items):
                desc = random.choice(category_info[2])
                qty = random.randint(1, 20)
                unit = round(remaining / qty * random.uniform(0.5, 1.0), 2)
                total = round(unit * qty, 2)
                items.append(
                    {
                        "id": generate_uuid(),
                        "po_id": po_id,
                        "description": desc,
                        "quantity": qty,
                        "unit_price": unit,
                        "total_price": total,
                    }
                )
                remaining -= total
                if remaining <= 0:
                    break

            pos.append(
                {
                    "id": po_id,
                    "po_number": po_number,
                    "contract_id": contract["id"],
                    "vendor_id": contract["vendor_id"],
                    "department_id": dept["id"],
                    "total_amount": float(po_amount),
                    "currency": contract.get("currency", "GBP"),
                    "status": random.choice(["approved", "approved", "approved", "fulfilled", "fulfilled"]),
                    "order_date": order_date.isoformat(),
                    "delivery_date": delivery_date.isoformat(),
                    "items": items,
                }
            )

    return pos


def generate_invoices(
    pos: list[dict],
    contracts: dict[str, dict],
    avg_invoices_per_po: int = 2,
) -> list[dict]:
    """Generate invoices linked to purchase orders."""
    invoices = []
    inv_counter = 1

    for po in pos:
        num_invoices = random.randint(1, avg_invoices_per_po * 2)
        for _ in range(num_invoices):
            contract = contracts.get(po["contract_id"], {})

            # Keep invoice dates inside the contract period and after the PO,
            # so normal data does not trip the expired-contract rule.
            try:
                c_start = date.fromisoformat(contract["start_date"])
                c_end = date.fromisoformat(contract["end_date"])
                po_date = date.fromisoformat(po["order_date"])
                start = max(c_start, po_date)
                end = min(c_end, date(2026, 10, 1))
                if start > end:
                    start, end = po_date, po_date + timedelta(days=30)
            except (KeyError, ValueError, TypeError):
                start, end = date(2024, 1, 1), date(2026, 10, 1)

            invoice_date = random_date(start, end)
            due_date = invoice_date + timedelta(days=random.choice([14, 30, 45, 60]))

            # Normal invoices never exceed the PO; anomalies are injected later.
            po_amount = po["total_amount"]
            amount = round(po_amount * random.uniform(0.70, 0.99), 2)

            inv_id = generate_uuid()
            inv_number = f"INV-{inv_counter:06d}"
            inv_counter += 1

            # Line items mirror PO items with slight variations
            items = []
            for po_item in po.get("items", []):
                items.append(
                    {
                        "id": generate_uuid(),
                        "invoice_id": inv_id,
                        "description": po_item["description"],
                        "quantity": po_item["quantity"],
                        "unit_price": po_item["unit_price"],
                        "total_price": round(po_item["quantity"] * po_item["unit_price"], 2),
                    }
                )

            invoices.append(
                {
                    "id": inv_id,
                    "invoice_number": inv_number,
                    "po_id": po["id"],
                    "vendor_id": po["vendor_id"],
                    "amount": amount,
                    "currency": po["currency"],
                    "invoice_date": invoice_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "status": "submitted",
                    "payment_status": "unpaid",
                    "items": items,
                }
            )

    return invoices


def generate_payments(
    invoices: list[dict],
    payment_rate: float = 0.85,
) -> list[dict]:
    """Generate payment records and derive consistent invoice statuses."""
    payments = []
    pay_counter = 1
    today = date.today()

    for inv in invoices:
        if random.random() > payment_rate:
            if inv.get("due_date") and date.fromisoformat(inv["due_date"]) < today:
                inv["status"] = "overdue"
            else:
                inv["status"] = "submitted"
            inv["payment_status"] = "unpaid"
            continue

        payment_date = datetime.fromisoformat(inv["invoice_date"]) + timedelta(days=random.randint(5, 45))

        pay_id = generate_uuid()
        pay_ref = f"PAY-{pay_counter:06d}"
        pay_counter += 1

        payments.append(
            {
                "id": pay_id,
                "payment_reference": pay_ref,
                "invoice_id": inv["id"],
                "amount": inv["amount"],
                "currency": inv["currency"],
                "payment_date": payment_date.isoformat(),
                "method": random.choice(["bank_transfer", "check", "card"]),
                "status": "completed",
            }
        )

        inv["status"] = "paid"
        inv["payment_status"] = "paid"

    return payments


def generate_approvals(
    invoices: list[dict],
    users: list[dict],
    approval_rate: float = 1.0,
) -> list[dict]:
    """Generate approval requests for invoices (clean by default)."""
    approvals = []
    appr_counter = 1

    for inv in invoices:
        if random.random() > approval_rate:
            continue

        requester = random.choice(users)
        approver = random.choice([u for u in users if u["role"] in ("manager", "director", "admin")])

        requested_date = datetime.fromisoformat(inv["invoice_date"])
        decided_date = requested_date + timedelta(days=random.randint(1, 7))

        appr_id = generate_uuid()
        appr_number = f"APPR-{appr_counter:06d}"
        appr_counter += 1

        approvals.append(
            {
                "id": appr_id,
                "approval_number": appr_number,
                "request_type": "invoice_approval",
                "invoice_id": inv["id"],
                "requested_by": requester["id"],
                "approved_by": approver["id"],
                "status": "approved",
                "justification": f"Invoice {inv['invoice_number']} requires approval per procurement policy",
                "requested_at": requested_date.isoformat(),
                "decided_at": decided_date.isoformat(),
            }
        )

    return approvals


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic enterprise data")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed"),
        help="Input directory with parsed public data",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic"),
        help="Output directory for synthetic data",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--num-users", type=int, default=50, help="Number of users to generate")
    parser.add_argument(
        "--pos-per-contract",
        type=int,
        default=3,
        help="Average POs per contract",
    )
    parser.add_argument(
        "--invoices-per-po",
        type=int,
        default=2,
        help="Average invoices per PO",
    )
    parser.add_argument(
        "--limit-contracts",
        type=int,
        default=None,
        help="Limit number of contracts to process (for testing)",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    logger.info(f"Using random seed: {args.seed}")

    # Load public data from processed directory
    # If args.input is data/synthetic, look in data/processed
    # If args.input is data/processed, use it directly
    if (args.input / "contracts.json").exists():
        contracts_path = args.input / "contracts.json"
    else:
        contracts_path = args.input.parent / "processed" / "contracts.json"

    if not contracts_path.exists():
        logger.error(f"Contracts file not found: {contracts_path}")
        logger.info("Run download_public_data.py first")
        sys.exit(1)

    with open(contracts_path) as f:
        contracts_list = json.load(f)
    logger.info(f"Loaded {len(contracts_list):,} contracts from {contracts_path}")

    # Only contracts overlapping the synthetic operating window can host
    # consistent POs/invoices dated inside the contract period.
    def _eligible(contract: dict) -> bool:
        try:
            start = date.fromisoformat(contract["start_date"])
            end = date.fromisoformat(contract["end_date"])
        except (KeyError, ValueError, TypeError):
            return False
        return end >= date(2024, 1, 1) and start <= date(2026, 6, 30)

    contracts_list = [c for c in contracts_list if _eligible(c)]
    logger.info(f"Eligible contracts (2024-2026): {len(contracts_list):,}")

    if args.limit_contracts:
        contracts_list = contracts_list[: args.limit_contracts]
        logger.info(f"Limited to {len(contracts_list):,} contracts")

    contracts_dict = {c["id"]: c for c in contracts_list}

    # Generate synthetic data
    logger.info("Generating departments...")
    departments = generate_departments()

    logger.info("Generating users...")
    users = generate_users(departments, args.num_users)

    logger.info("Generating purchase orders...")
    pos = generate_purchase_orders(contracts_list, departments, args.pos_per_contract)

    logger.info("Generating invoices...")
    invoices = generate_invoices(pos, contracts_dict, args.invoices_per_po)

    logger.info("Generating payments...")
    payments = generate_payments(invoices)

    logger.info("Generating approvals...")
    approvals = generate_approvals(invoices, users)

    # Save all data
    args.output.mkdir(parents=True, exist_ok=True)

    datasets = {
        "departments": departments,
        "users": users,
        "purchase_orders": pos,
        "invoices": invoices,
        "payments": payments,
        "approvals": approvals,
    }

    for name, data in datasets.items():
        output_path = args.output / f"{name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved {len(data):,} {name} to {output_path}")

    logger.info("Synthetic data generation complete!")
    logger.info(f"  Departments: {len(departments)}")
    logger.info(f"  Users: {len(users)}")
    logger.info(f"  Purchase Orders: {len(pos):,}")
    logger.info(f"  Invoices: {len(invoices):,}")
    logger.info(f"  Payments: {len(payments):,}")
    logger.info(f"  Approvals: {len(approvals):,}")


if __name__ == "__main__":
    main()
