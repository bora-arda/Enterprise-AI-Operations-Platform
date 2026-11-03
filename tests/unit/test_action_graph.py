"""Unit tests for the checkpointed action-execution graph."""

from langgraph.checkpoint.memory import MemorySaver

from procurement_ai.graph.action_execution import build_action_graph


class TestActionExecutionGraph:
    def test_graph_compiles(self):
        graph = build_action_graph(MemorySaver())
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_action_graph(MemorySaver())
        node_names = set(graph.get_graph().nodes.keys())
        assert "validate" in node_names
        assert "policy_check" in node_names
        assert "risk_assess" in node_names
        assert "create_approval" in node_names
        assert "await_decision" in node_names
        assert "execute" in node_names
        assert "reject" in node_names
