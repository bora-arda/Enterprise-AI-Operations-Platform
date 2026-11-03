"""Unit tests for anomaly detection rules."""

from procurement_ai.anomaly_detection.rules import (
    invoice_exceeds_po,
    payment_mismatch,
    run_all_rules,
    wrong_currency,
    wrong_vendor,
)


class TestAnomalyRules:
    def test_invoice_exceeds_po(self):
        invoice = {"amount": 20000, "invoice_number": "INV-001"}
        po = {"total_amount": 15000, "po_number": "PO-001"}
        result = invoice_exceeds_po(invoice, po)
        assert result is not None
        assert result["rule"] == "invoice_exceeds_po"

    def test_invoice_within_po(self):
        invoice = {"amount": 10000}
        po = {"total_amount": 15000}
        result = invoice_exceeds_po(invoice, po)
        assert result is None

    def test_wrong_vendor(self):
        invoice = {"vendor_id": "vendor-001"}
        po = {"vendor_id": "vendor-002"}
        result = wrong_vendor(invoice, po)
        assert result is not None
        assert result["rule"] == "wrong_vendor"

    def test_wrong_currency(self):
        invoice = {"currency": "USD"}
        po = {"currency": "GBP"}
        result = wrong_currency(invoice, po)
        assert result is not None
        assert result["rule"] == "wrong_currency"

    def test_payment_mismatch(self):
        payment = {"amount": 8000}
        invoice = {"amount": 10000}
        result = payment_mismatch(payment, invoice)
        assert result is not None
        assert result["rule"] == "payment_mismatch"

    def test_run_all_rules_clean(self):
        invoice = {
            "id": "inv-001",
            "amount": 10000,
            "currency": "GBP",
            "vendor_id": "vendor-001",
            "po_id": "po-001",
            "invoice_date": "2025-06-01",
            "due_date": "2025-07-01",
        }
        po = {"id": "po-001", "total_amount": 15000, "vendor_id": "vendor-001", "currency": "GBP"}
        contract = {"id": "contract-001", "max_value": 120000, "end_date": "2025-12-31"}
        anomalies = run_all_rules(invoice, po, contract, [])
        assert len(anomalies) == 0
