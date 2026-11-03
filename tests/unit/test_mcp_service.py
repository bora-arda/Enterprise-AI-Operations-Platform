"""Unit tests for the mock ERP service."""

from procurement_ai.mcp import service


class TestMockERPService:
    def setup_method(self):
        service.reset_state()

    def test_create_payment_request(self):
        record = service.create_payment_request(
            payment_reference="PAY-TEST-1",
            invoice_id="inv-1",
            amount=100.0,
            currency="GBP",
        )
        assert record["payment_reference"] == "PAY-TEST-1"
        assert record["status"] == "submitted"
        assert record["amount"] == 100.0

    def test_payment_request_is_idempotent(self):
        first = service.create_payment_request("PAY-TEST-2", "inv-2", 50.0, "GBP")
        second = service.create_payment_request("PAY-TEST-2", "inv-2", 50.0, "GBP")
        assert first is second

    def test_get_payment_status(self):
        service.create_payment_request("PAY-TEST-3", "inv-3", 75.0, "EUR")
        record = service.get_payment_status("PAY-TEST-3")
        assert record is not None
        assert record["currency"] == "EUR"

    def test_get_unknown_payment_returns_none(self):
        assert service.get_payment_status("PAY-MISSING") is None

    def test_create_exception(self):
        record = service.create_exception("duplicate_invoice", "inv-4", "test")
        assert record["status"] == "open"
        assert record["entity_id"] == "inv-4"

    def test_update_workflow_status(self):
        record = service.update_workflow_status("wf-1", "approved", "ok")
        assert record["status"] == "approved"
        assert record["comment"] == "ok"
