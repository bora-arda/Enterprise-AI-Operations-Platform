"""Unit tests for entity reference extraction."""

from procurement_ai.graph.nodes.entity_lookup import (
    extract_entity_reference,
    extract_vendor_name,
)


class TestEntityReferenceExtraction:
    def test_invoice(self):
        assert extract_entity_reference("Why is INV-000123 overdue?") == (
            "invoice",
            "INV-000123",
        )

    def test_purchase_order(self):
        assert extract_entity_reference("Show me PO-000456") == (
            "purchase_order",
            "PO-000456",
        )

    def test_contract(self):
        assert extract_entity_reference("What is contract CF-2022-00001?") == (
            "contract",
            "CF-2022-00001",
        )

    def test_payment(self):
        assert extract_entity_reference("Status of PAY-000123") == (
            "payment",
            "PAY-000123",
        )

    def test_approval(self):
        assert extract_entity_reference("Show approval APPR-ABC12345") == (
            "approval",
            "APPR-ABC12345",
        )

    def test_none(self):
        assert extract_entity_reference("What are the approval requirements?") is None


class TestVendorNameExtraction:
    def test_vendor_prefix(self):
        assert extract_vendor_name("What are the payment terms for vendor Acme Ltd?") == ("Acme Ltd")

    def test_supplier_prefix(self):
        assert extract_vendor_name("Show contracts for supplier Northwind") == "Northwind"

    def test_no_vendor(self):
        assert extract_vendor_name("Which invoices are overdue?") is None
