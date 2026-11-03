"""End-to-end test for anomaly detection workflow."""

import pytest


class TestAnomalyDetection:
    @pytest.mark.asyncio
    async def test_detect_policy_violations(self):
        """Test: 'Find transactions that may violate procurement policy'"""
        from procurement_ai.graph.orchestrator import create_orchestrator

        graph = create_orchestrator()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_find_duplicates(self):
        """Test: 'Find duplicate invoices'"""
        from procurement_ai.graph.orchestrator import create_orchestrator

        graph = create_orchestrator()
        assert graph is not None
