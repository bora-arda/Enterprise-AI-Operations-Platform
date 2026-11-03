"""Integration tests for action workflow with approval."""

import pytest

from procurement_ai.graph.nodes.action import action_workflow_node


class TestActionWorkflow:
    @pytest.mark.asyncio
    async def test_action_workflow_node(self):
        state = {
            "user_input": "Request payment for INV-000001",
            "user_id": "user-001",
            "session_id": "sess-001",
            "intent": "act",
            "workflow": "action",
            "evidence": [],
            "citations": [],
            "response": "",
            "errors": [],
            "approval_status": "not_required",
            "tool_results": [],
        }
        result = await action_workflow_node(state)
        assert "response" in result
        assert result["response"]
        assert "approval_status" in result
