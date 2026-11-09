"""Tests for exception tool normalization (no database required)."""

from procurement_ai.agent.tools import _normalize_exception_type


class TestExceptionNormalization:
    def test_natural_aliases(self):
        assert _normalize_exception_type("invoice exceeds po") == "invoice_exceeds_po"
        assert _normalize_exception_type("missing approvals") == "missing_approval"
        assert _normalize_exception_type("already paid") == "already_paid"
        assert _normalize_exception_type("duplicate invoices") == "duplicate_invoice"

    def test_canonical_names(self):
        assert _normalize_exception_type("invoice_exceeds_contract") == "invoice_exceeds_contract"
        assert _normalize_exception_type("payment-mismatch") == "payment_mismatch"

    def test_unknown_passes_through(self):
        assert _normalize_exception_type("something else") == "something else"
