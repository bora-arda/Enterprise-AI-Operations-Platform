#!/usr/bin/env python3
"""
Load processed and synthetic data into PostgreSQL.

Reads JSON files from data/processed/ and data/synthetic/ and inserts
them into the database using SQLAlchemy.
"""

import argparse
import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_date(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.split("T")[0])
        except (ValueError, IndexError):
            return None
    return value


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    return value


def parse_uuid(value):
    if not value:
        return str(uuid.uuid4())
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return str(uuid.uuid4())


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return []
    with open(path) as f:
        return json.load(f)


def load_buyers(session, data: list[dict]) -> dict:
    """Load buyers and return mapping of old_id -> new_uuid."""
    from procurement_ai.database.models import Buyer

    id_map = {}
    for item in data:
        buyer = Buyer(
            id=parse_uuid(item.get("id")),
            name=item.get("name", ""),
            country=item.get("country"),
            identifier=item.get("id"),
            source=item.get("source"),
        )
        session.add(buyer)
        id_map[item["id"]] = buyer.id
    session.flush()
    logger.info(f"Loaded {len(data)} buyers")
    return id_map


def load_vendors(session, data: list[dict]) -> dict:
    """Load vendors and return mapping of old_id -> new_uuid."""
    from procurement_ai.database.models import Vendor

    id_map = {}
    for item in data:
        vendor = Vendor(
            id=parse_uuid(item.get("id")),
            name=item.get("name", ""),
            tax_id=item.get("tax_id"),
            country=item.get("country"),
            status=item.get("status", "active"),
            bank_details=item.get("bank_details"),
            source=item.get("source"),
        )
        session.add(vendor)
        id_map[item["id"]] = vendor.id
    session.flush()
    logger.info(f"Loaded {len(data)} vendors")
    return id_map


def load_contracts(session, data: list[dict], buyer_map: dict, vendor_map: dict) -> dict:
    """Load contracts and return mapping of old_id -> new_uuid."""
    from procurement_ai.database.models import Contract

    id_map = {}
    seen_contract_numbers = set()
    skipped = 0

    for item in data:
        contract_number = item.get("contract_number", "")

        # Skip duplicates (same contract number)
        if contract_number in seen_contract_numbers:
            skipped += 1
            continue

        seen_contract_numbers.add(contract_number)

        title = item.get("title", "")[:500]  # Truncate to fit VARCHAR(500)
        description = item.get("description")
        if description and len(description) > 10000:
            description = description[:10000]

        contract = Contract(
            id=parse_uuid(item.get("id")),
            contract_number=contract_number,
            title=title,
            description=description,
            vendor_id=vendor_map.get(item.get("vendor_id")),
            buyer_id=buyer_map.get(item.get("buyer_id")),
            value=Decimal(str(item["value"])) if item.get("value") else None,
            max_value=Decimal(str(item["max_value"])) if item.get("max_value") else None,
            currency=item.get("currency"),
            start_date=parse_date(item.get("start_date")),
            end_date=parse_date(item.get("end_date")),
            published_date=parse_date(item.get("published_date")),
            category=item.get("category"),
            category_description=item.get("category_description"),
            procurement_method=item.get("procurement_method"),
            status=item.get("status", "active"),
            payment_terms=item.get("payment_terms"),
            terms=item.get("terms"),
            source=item.get("source"),
            source_reference=item.get("source_reference"),
        )
        session.add(contract)
        id_map[item["id"]] = contract.id

    session.flush()
    logger.info(f"Loaded {len(id_map)} contracts (skipped {skipped} duplicates)")
    return id_map


def load_departments(session, data: list[dict]) -> dict:
    """Load departments and return mapping of old_id -> new_uuid."""
    from procurement_ai.database.models import Department

    id_map = {}
    for item in data:
        dept = Department(
            id=parse_uuid(item.get("id")),
            name=item.get("name", ""),
            code=item.get("code", ""),
            budget_limit=Decimal(str(item["budget_limit"])) if item.get("budget_limit") else None,
        )
        session.add(dept)
        id_map[item["id"]] = dept.id
    session.flush()
    logger.info(f"Loaded {len(data)} departments")
    return id_map


def load_users(session, data: list[dict], dept_map: dict) -> dict:
    """Load users and return mapping of old_id -> new_uuid."""
    from procurement_ai.database.models import User

    id_map = {}
    for item in data:
        user = User(
            id=parse_uuid(item.get("id")),
            name=item.get("name", ""),
            email=item.get("email", ""),
            role=item.get("role", "specialist"),
            department_id=dept_map.get(item.get("department_id")),
        )
        session.add(user)
        id_map[item["id"]] = user.id
    session.flush()
    logger.info(f"Loaded {len(data)} users")
    return id_map


def load_purchase_orders(session, data: list[dict], contract_map: dict, vendor_map: dict, dept_map: dict) -> dict:
    """Load purchase orders and return mapping of old_id -> new_uuid."""
    from procurement_ai.database.models import PurchaseOrder, PurchaseOrderItem

    id_map = {}
    for item in data:
        po = PurchaseOrder(
            id=parse_uuid(item.get("id")),
            po_number=item.get("po_number", ""),
            contract_id=contract_map.get(item.get("contract_id")),
            vendor_id=vendor_map.get(item.get("vendor_id")),
            department_id=dept_map.get(item.get("department_id")),
            total_amount=Decimal(str(item["total_amount"])) if item.get("total_amount") else Decimal("0"),
            currency=item.get("currency"),
            status=item.get("status", "draft"),
            order_date=parse_date(item.get("order_date")),
            delivery_date=parse_date(item.get("delivery_date")),
        )
        session.add(po)
        id_map[item["id"]] = po.id

        # Load line items
        for line_item in item.get("items", []):
            po_item = PurchaseOrderItem(
                id=parse_uuid(line_item.get("id")),
                po_id=po.id,
                description=line_item.get("description"),
                quantity=line_item.get("quantity"),
                unit_price=Decimal(str(line_item["unit_price"])) if line_item.get("unit_price") else None,
                total_price=Decimal(str(line_item["total_price"])) if line_item.get("total_price") else None,
            )
            session.add(po_item)
    session.flush()
    logger.info(f"Loaded {len(data)} purchase orders")
    return id_map


def load_invoices(session, data: list[dict], po_map: dict, vendor_map: dict) -> dict:
    """Load invoices and return mapping of old_id -> new_uuid."""

    from procurement_ai.database.models import Invoice, InvoiceItem

    id_map = {}
    seen_item_ids = set()
    skipped_items = 0

    for item in data:
        invoice = Invoice(
            id=parse_uuid(item.get("id")),
            invoice_number=item.get("invoice_number", ""),
            po_id=po_map.get(item.get("po_id")),
            vendor_id=vendor_map.get(item.get("vendor_id")),
            amount=Decimal(str(item["amount"])) if item.get("amount") else Decimal("0"),
            currency=item.get("currency"),
            invoice_date=parse_date(item.get("invoice_date")),
            due_date=parse_date(item.get("due_date")),
            status=item.get("status", "draft"),
            payment_status=item.get("payment_status", "unpaid"),
        )
        session.add(invoice)
        id_map[item["id"]] = invoice.id

        # Load line items (skip duplicates)
        for line_item in item.get("items", []):
            item_id = parse_uuid(line_item.get("id"))
            if item_id in seen_item_ids:
                skipped_items += 1
                continue
            seen_item_ids.add(item_id)

            inv_item = InvoiceItem(
                id=item_id,
                invoice_id=invoice.id,
                description=line_item.get("description"),
                quantity=line_item.get("quantity"),
                unit_price=Decimal(str(line_item["unit_price"])) if line_item.get("unit_price") else None,
                total_price=Decimal(str(line_item["total_price"])) if line_item.get("total_price") else None,
            )
            session.add(inv_item)

    session.flush()
    logger.info(f"Loaded {len(data)} invoices (skipped {skipped_items} duplicate items)")
    return id_map


def load_payments(session, data: list[dict], invoice_map: dict) -> None:
    """Load payments."""
    from procurement_ai.database.models import Payment

    for item in data:
        payment = Payment(
            id=parse_uuid(item.get("id")),
            payment_reference=item.get("payment_reference", ""),
            invoice_id=invoice_map.get(item.get("invoice_id")),
            amount=Decimal(str(item["amount"])) if item.get("amount") else Decimal("0"),
            currency=item.get("currency"),
            payment_date=parse_date(item.get("payment_date")),
            method=item.get("method"),
            status=item.get("status", "pending"),
        )
        session.add(payment)
    session.flush()
    logger.info(f"Loaded {len(data)} payments")


def load_approvals(session, data: list[dict], invoice_map: dict, user_map: dict) -> None:
    """Load approval requests."""
    from procurement_ai.database.models import ApprovalRequest

    for item in data:
        approval = ApprovalRequest(
            id=parse_uuid(item.get("id")),
            approval_number=item.get("approval_number", ""),
            request_type=item.get("request_type"),
            invoice_id=invoice_map.get(item.get("invoice_id")),
            requested_by=user_map.get(item.get("requested_by")),
            approved_by=user_map.get(item.get("approved_by")),
            status=item.get("status", "pending"),
            justification=item.get("justification"),
            requested_at=parse_datetime(item.get("requested_at")),
            decided_at=parse_datetime(item.get("decided_at")),
        )
        session.add(approval)
    session.flush()
    logger.info(f"Loaded {len(data)} approval requests")


def main():
    parser = argparse.ArgumentParser(description="Load data into PostgreSQL")
    parser.add_argument("--database-url", default="postgresql+asyncpg://user:pass@localhost:5432/procurement")
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--synthetic-dir", type=Path, default=Path("data/synthetic"))
    args = parser.parse_args()

    # Create engine (sync for loading)
    engine = create_engine(args.database_url.replace("+asyncpg", "+psycopg2"))
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Load in dependency order
        buyers = load_json(args.processed_dir / "buyers.json")
        vendors = load_json(args.processed_dir / "vendors.json")
        contracts = load_json(args.processed_dir / "contracts.json")
        departments = load_json(args.synthetic_dir / "departments.json")
        users = load_json(args.synthetic_dir / "users.json")
        pos = load_json(args.synthetic_dir / "purchase_orders.json")
        invoices = load_json(args.synthetic_dir / "invoices.json")
        payments = load_json(args.synthetic_dir / "payments.json")
        approvals = load_json(args.synthetic_dir / "approvals.json")

        buyer_map = load_buyers(session, buyers)
        vendor_map = load_vendors(session, vendors)
        contract_map = load_contracts(session, contracts, buyer_map, vendor_map)
        dept_map = load_departments(session, departments)
        user_map = load_users(session, users, dept_map)
        po_map = load_purchase_orders(session, pos, contract_map, vendor_map, dept_map)
        invoice_map = load_invoices(session, invoices, po_map, vendor_map)
        load_payments(session, payments, invoice_map)
        load_approvals(session, approvals, invoice_map, user_map)

        session.commit()
        logger.info("All data loaded successfully!")

    except Exception as e:
        session.rollback()
        logger.error(f"Error loading data: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
