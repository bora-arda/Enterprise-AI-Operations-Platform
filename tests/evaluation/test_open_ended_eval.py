"""Tests for open-ended agent evaluation metrics (no LLM/database required)."""

from procurement_ai.evaluation.open_ended_eval import (
    answer_coverage,
    evaluate_open_ended,
    sql_guard_block_rate,
    tool_success_rate,
)


class TestOpenEndedMetrics:
    def test_answer_coverage(self):
        assert answer_coverage(["invoice", "vendor"], "Invoice INV-1 vendor Acme") == 1.0
        assert answer_coverage(["invoice", "vendor"], "Invoice INV-1") == 0.5
        assert answer_coverage([], "anything") == 1.0

    def test_tool_success_rate(self):
        traces = [{"success": True}, {"success": False}, {"success": True}]
        assert tool_success_rate(traces) == 2 / 3
        assert tool_success_rate([]) == 1.0

    def test_sql_guard_block_rate(self):
        statements = ["SELECT 1", "DROP TABLE invoices", "SELECT pg_sleep(1)"]
        assert sql_guard_block_rate(statements) == 2 / 3

    def test_evaluate_open_ended(self):
        benchmark = [
            {
                "id": "a",
                "expected_workflow": "agent",
                "expected_tools": ["query_database"],
                "required_terms": ["vendor"],
            },
            {
                "id": "b",
                "expected_workflow": "agent",
                "expected_tools": ["query_database"],
                "required_terms": ["contract"],
            },
        ]
        results = {
            "a": {
                "workflow": "agent",
                "tools_used": ["query_database"],
                "tool_traces": [{"success": True}],
                "answer": "Top vendors",
                "steps": 3,
            },
            "b": {
                "workflow": "sql",
                "tools_used": [],
                "tool_traces": [],
                "answer": "No data",
                "steps": 0,
            },
        }
        metrics = evaluate_open_ended(benchmark, results)
        assert metrics["routing_accuracy"] == 0.5
        assert metrics["tool_selection_accuracy"] == 0.5
        assert metrics["answer_term_coverage"] == 0.5
        assert metrics["tool_success_rate"] == 1.0
        assert metrics["average_agent_steps"] == 1.5
