"""Evaluation tests for agent metrics."""

from procurement_ai.evaluation.agent_eval import (
    routing_accuracy,
    tool_selection_accuracy,
    workflow_completion,
)


class TestAgentMetrics:
    def test_tool_selection_perfect(self):
        expected = ["get_invoice", "get_po"]
        actual = ["get_invoice", "get_po"]
        assert tool_selection_accuracy(expected, actual) == 1.0

    def test_tool_selection_partial(self):
        expected = ["get_invoice", "get_po", "get_contract"]
        actual = ["get_invoice", "get_po"]
        assert tool_selection_accuracy(expected, actual) == 2 / 3

    def test_routing_correct(self):
        assert routing_accuracy("investigation", "investigation") == 1.0

    def test_routing_incorrect(self):
        assert routing_accuracy("investigation", "retrieval") == 0.0

    def test_workflow_completion(self):
        assert workflow_completion(3, 3) == 1.0
        assert workflow_completion(3, 2) == 2 / 3
