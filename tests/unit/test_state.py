"""Unit tests for agent state and orchestrator."""

from procurement_ai.graph.orchestrator import create_orchestrator
from procurement_ai.graph.state import AgentState


class TestAgentState:
    def test_state_creation(self):
        state = AgentState(
            user_input="test",
            user_id="user-1",
            session_id="sess-1",
            history=[],
            last_invoice_number=None,
            intent="",
            workflow="",
            evidence=[],
            citations=[],
            tool_calls=[],
            tool_results=[],
            action_request=None,
            approval_status="not_required",
            approval_decision=None,
            response="",
            confidence=None,
            errors=[],
            trace_id="trace-1",
            node_latencies={},
        )
        assert state["user_input"] == "test"
        assert state["errors"] == []


class TestOrchestrator:
    def test_create_orchestrator(self):
        graph = create_orchestrator()
        assert graph is not None
