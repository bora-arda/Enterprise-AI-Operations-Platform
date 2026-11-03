#!/usr/bin/env python3
"""
Build evaluation benchmark datasets.

Creates:
- retrieval_benchmark.json — queries with expected sources
- sql_benchmark.json — questions with expected SQL results
- compliance_benchmark.json — compliance check cases
- agent_benchmark.json — agent tasks with expected tool calls
"""

import argparse
import json
import logging
import random
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_retrieval_benchmark(documents: list[dict], size: int = 200) -> list[dict]:
    """Build retrieval evaluation benchmark."""
    benchmark = []
    docs_by_type = {}
    for doc in documents:
        doc_type = doc.get("document_type", "unknown")
        if doc_type not in docs_by_type:
            docs_by_type[doc_type] = []
        docs_by_type[doc_type].append(doc)

    # Generate queries for each document type
    for doc_type, docs in docs_by_type.items():
        sample = random.sample(docs, min(size // len(docs_by_type), len(docs)))
        for doc in sample:
            title = doc.get("title", "")

            # Create a query based on document content
            if doc_type == "contract":
                query = f"What are the payment terms and contract value for {doc.get('metadata', {}).get('vendor_name', 'this vendor')}?"
                expected_source = doc["id"]
            elif doc_type == "invoice":
                query = f"Show me details for invoice {doc.get('metadata', {}).get('invoice_number', 'unknown')}"
                expected_source = doc["id"]
            elif doc_type == "policy":
                query = f"What does the {title.lower()} say about approval requirements?"
                expected_source = doc["id"]
            else:
                query = f"Find information about {title}"
                expected_source = doc["id"]

            benchmark.append(
                {
                    "query": query,
                    "expected_sources": [expected_source],
                    "document_type": doc_type,
                    "metadata": {"document_id": doc["id"]},
                }
            )

    return benchmark


def build_sql_benchmark(invoices: list[dict], pos: list[dict], contracts: list[dict], size: int = 100) -> list[dict]:
    """Build SQL reasoning benchmark."""
    benchmark = []
    po_dict = {p["id"]: p for p in pos}

    # Sample invoices for benchmark
    sample = random.sample(invoices, min(size, len(invoices)))

    for inv in sample:
        po = po_dict.get(inv.get("po_id"))
        if not po:
            continue

        benchmark.append(
            {
                "question": f"What is the status of invoice {inv['invoice_number']}?",
                "expected_sql": f"SELECT status FROM invoices WHERE invoice_number = '{inv['invoice_number']}'",
                "expected_result": {"status": inv["status"]},
                "expected_facts": [
                    f"Invoice {inv['invoice_number']} has status {inv['status']}",
                    f"Amount: {inv['amount']} {inv['currency']}",
                ],
            }
        )

        benchmark.append(
            {
                "question": f"Which invoices are overdue for PO {po['po_number']}?",
                "expected_sql": f"SELECT * FROM invoices WHERE po_id = '{po['id']}' AND status = 'overdue'",
                "expected_result": {
                    "count": sum(1 for i in invoices if i.get("po_id") == po["id"] and i["status"] == "overdue")
                },
                "expected_facts": [
                    f"PO {po['po_number']} has {sum(1 for i in invoices if i.get('po_id') == po['id'] and i['status'] == 'overdue')} overdue invoices",
                ],
            }
        )

    return benchmark


def build_compliance_benchmark(invoices: list[dict], pos: dict, contracts: dict, size: int = 50) -> list[dict]:
    """Build compliance check benchmark."""
    benchmark = []
    pos_dict = pos if isinstance(pos, dict) else {p["id"]: p for p in pos}

    for inv in random.sample(invoices, min(size, len(invoices))):
        po = pos_dict.get(inv.get("po_id"))
        if not po:
            continue
        contract = contracts.get(po.get("contract_id"))

        issues = []
        if inv["amount"] > po["total_amount"]:
            issues.append("Invoice amount exceeds PO amount")
        if contract and contract.get("max_value") and inv["amount"] > contract["max_value"]:
            issues.append("Invoice amount exceeds contract limit")
        if inv.get("vendor_id") != po.get("vendor_id"):
            issues.append("Vendor mismatch between invoice and PO")

        benchmark.append(
            {
                "question": f"Does invoice {inv['invoice_number']} comply with its purchase order and contract?",
                "invoice_id": inv["id"],
                "po_id": po["id"],
                "contract_id": po.get("contract_id"),
                "expected_result": "compliant" if not issues else "non_compliant",
                "expected_issues": issues,
                "expected_facts": [
                    f"Invoice amount: {inv['amount']}",
                    f"PO amount: {po['total_amount']}",
                    f"Contract max: {contract.get('max_value') if contract else 'N/A'}",
                ],
            }
        )

    return benchmark


def build_agent_benchmark(invoices: list[dict], pos: dict, payments: list[dict], size: int = 100) -> list[dict]:
    """Build agent evaluation benchmark."""
    benchmark = []
    po_dict = pos if isinstance(pos, dict) else {p["id"]: p for p in pos}
    payment_dict = {p["invoice_id"]: p for p in payments}

    for inv in random.sample(invoices, min(size, len(invoices))):
        po = po_dict.get(inv.get("po_id"))
        payment = payment_dict.get(inv["id"])

        # Determine expected workflow and tools
        if inv["status"] == "overdue" and not payment:
            expected_workflow = "investigation"
            expected_tools = [
                "get_invoice",
                "get_purchase_order",
                "get_payment_status",
                "search_documents",
            ]
            question = f"Why is invoice {inv['invoice_number']} overdue?"
        elif inv["amount"] > (po["total_amount"] if po else 0):
            expected_workflow = "investigation"
            expected_tools = ["get_invoice", "get_purchase_order", "check_policy"]
            question = f"Does invoice {inv['invoice_number']} comply with its PO?"
        elif payment:
            expected_workflow = "retrieval"
            expected_tools = ["get_invoice", "get_payment_status"]
            question = f"What is the payment status of invoice {inv['invoice_number']}?"
        else:
            expected_workflow = "retrieval"
            expected_tools = ["get_invoice"]
            question = f"Show me the details of invoice {inv['invoice_number']}"

        benchmark.append(
            {
                "question": question,
                "expected_workflow": expected_workflow,
                "expected_tools": expected_tools,
                "expected_facts": [
                    f"Invoice {inv['invoice_number']} amount: {inv['amount']}",
                    f"Status: {inv['status']}",
                ],
                "invoice_id": inv["id"],
            }
        )

    return benchmark


def main():
    parser = argparse.ArgumentParser(description="Build evaluation benchmark datasets")
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
        help="Output directory for benchmarks",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    def load_json(name: str, base: Path = None) -> list[dict]:
        base = base or args.input
        path = base / f"{name}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    invoices = load_json("invoices")
    pos = load_json("purchase_orders")
    contracts = load_json("contracts")
    payments = load_json("payments")

    # Load documents from processed directory
    docs_path = args.input.parent / "processed" / "documents" / "documents.json"
    documents = []
    if docs_path.exists():
        with open(docs_path) as f:
            documents = json.load(f)

    pos_dict = {p["id"]: p for p in pos}
    contracts_dict = {c["id"]: c for c in contracts}

    logger.info("Building evaluation benchmarks...")

    args.output.mkdir(parents=True, exist_ok=True)

    # Build benchmarks
    retrieval = build_retrieval_benchmark(documents)
    with open(args.output / "retrieval_benchmark.json", "w") as f:
        json.dump(retrieval, f, indent=2)
    logger.info(f"  retrieval_benchmark.json: {len(retrieval)} queries")

    sql = build_sql_benchmark(invoices, pos, contracts)
    with open(args.output / "sql_benchmark.json", "w") as f:
        json.dump(sql, f, indent=2)
    logger.info(f"  sql_benchmark.json: {len(sql)} questions")

    compliance = build_compliance_benchmark(invoices, pos_dict, contracts_dict)
    with open(args.output / "compliance_benchmark.json", "w") as f:
        json.dump(compliance, f, indent=2)
    logger.info(f"  compliance_benchmark.json: {len(compliance)} cases")

    agent = build_agent_benchmark(invoices, pos_dict, payments)
    with open(args.output / "agent_benchmark.json", "w") as f:
        json.dump(agent, f, indent=2)
    logger.info(f"  agent_benchmark.json: {len(agent)} tasks")

    logger.info("Evaluation benchmark generation complete!")


if __name__ == "__main__":
    main()
