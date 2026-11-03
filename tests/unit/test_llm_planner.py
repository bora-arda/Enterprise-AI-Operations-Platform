"""Unit tests for LLM planner validation (no network calls)."""

import asyncio

from procurement_ai.planner.llm_planner import (
    _extract_json,
    plan_request,
    validate_decision,
)


class TestPlannerValidation:
    def test_valid_investigation(self):
        decision = validate_decision(
            {
                "workflow": "investigation",
                "intent": "investigate",
                "entity": {"type": "invoice", "id": "INV-000010"},
                "metric": {"name": None},
                "follow_up": False,
                "reason": "overdue invoice",
            }
        )
        assert decision is not None
        assert decision.workflow == "investigation"
        assert decision.entity_type == "invoice"
        assert decision.entity_id == "INV-000010"

    def test_valid_metric(self):
        decision = validate_decision(
            {
                "workflow": "sql",
                "intent": "analyze",
                "metric": {
                    "name": "exception_rate",
                    "dimension": "vendor",
                    "days": 90,
                },
            }
        )
        assert decision.metric == "exception_rate"
        assert decision.dimension == "vendor"
        assert decision.days == 90

    def test_invalid_workflow_rejected(self):
        assert validate_decision({"workflow": "delete_everything"}) is None
        assert validate_decision(None) is None

    def test_invalid_metric_cleared(self):
        decision = validate_decision({"workflow": "sql", "intent": "analyze", "metric": {"name": "drop_tables"}})
        assert decision is not None
        assert decision.metric is None

    def test_disallowed_dimension_cleared(self):
        decision = validate_decision(
            {
                "workflow": "sql",
                "metric": {"name": "overdue_rate", "dimension": "exception_type"},
            }
        )
        assert decision.dimension is None

    def test_invalid_entity_id_cleared(self):
        decision = validate_decision(
            {
                "workflow": "retrieval",
                "entity": {"type": "invoice", "id": "PO-000001"},
            }
        )
        assert decision.entity_type == "invoice"
        assert decision.entity_id is None

    def test_clarification_default_message(self):
        decision = validate_decision({"workflow": "clarification", "clarification_message": ""})
        assert decision.clarification_message
        assert "identifier" in decision.clarification_message.lower()

    def test_days_out_of_range_cleared(self):
        decision = validate_decision(
            {
                "workflow": "sql",
                "metric": {"name": "total_spend", "days": 999999},
            }
        )
        assert decision.days is None

    def test_extract_json_with_fences(self):
        payload = _extract_json('```json\n{"workflow": "fallback"}\n```')
        assert payload == {"workflow": "fallback"}

    def test_extract_json_invalid(self):
        assert _extract_json("not json") is None


class TestPlannerFallback:
    def test_deterministic_mode_returns_no_decision(self):
        # conftest sets PLANNER_MODE=deterministic for the test suite
        outcome = asyncio.run(plan_request("Why is INV-000001 overdue?", []))
        assert outcome.decision is None
        assert outcome.planner_mode == "deterministic"
        assert outcome.validation_result == "deterministic"
        assert outcome.fallback_used is False
