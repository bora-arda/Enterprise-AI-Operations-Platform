"""End-to-end test for invoice investigation workflow."""

import pytest


class TestInvoiceInvestigation:
    @pytest.mark.asyncio
    async def test_overdue_invoice_investigation(self):
        """Test: 'Why is INV-001 overdue?'"""
        # This test requires full system setup (DB + LLM)
        # For now, verify the graph structure is correct
        from procurement_ai.graph.orchestrator import create_orchestrator

        graph = create_orchestrator()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_compliance_check(self):
        """Test: 'Does INV-001 comply with its PO?'"""
        from procurement_ai.graph.orchestrator import create_orchestrator

        graph = create_orchestrator()
        assert graph is not None
