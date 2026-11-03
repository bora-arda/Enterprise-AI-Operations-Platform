"""Shared test fixtures."""

import os

import pytest

# Tests must not create Postgres checkpointers (they are event-loop bound and
# would be reused across TestClient loops). Production memory stays enabled.
os.environ.setdefault("CHAT_MEMORY_ENABLED", "false")
# Never make live LLM calls from the test suite.
os.environ.setdefault("PLANNER_MODE", "deterministic")


@pytest.fixture
def sample_invoice():
    return {
        "id": "inv-001",
        "invoice_number": "INV-001",
        "po_id": "po-001",
        "vendor_id": "vendor-001",
        "amount": 15000.0,
        "currency": "GBP",
        "invoice_date": "2025-06-01",
        "due_date": "2025-07-01",
        "status": "submitted",
        "payment_status": "unpaid",
    }


@pytest.fixture
def sample_po():
    return {
        "id": "po-001",
        "po_number": "PO-001",
        "contract_id": "contract-001",
        "vendor_id": "vendor-001",
        "department_id": "dept-001",
        "total_amount": 20000.0,
        "currency": "GBP",
        "status": "approved",
        "order_date": "2025-05-01",
        "delivery_date": "2025-06-01",
    }


@pytest.fixture
def sample_contract():
    return {
        "id": "contract-001",
        "contract_number": "CF-2025-00001",
        "title": "IT Services Contract",
        "vendor_id": "vendor-001",
        "buyer_id": "buyer-001",
        "value": 100000.0,
        "max_value": 120000.0,
        "currency": "GBP",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "status": "active",
    }


@pytest.fixture
def sample_state():
    return {
        "user_input": "Why is INV-001 overdue?",
        "user_id": "user-001",
        "session_id": "sess-001",
        "intent": "investigate",
        "workflow": "investigation",
        "evidence": [],
        "citations": [],
        "tool_calls": [],
        "tool_results": [],
        "response": "",
        "confidence": None,
        "errors": [],
        "trace_id": "trace-001",
    }
