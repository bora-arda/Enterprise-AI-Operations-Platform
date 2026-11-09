"""Unit tests for LLM planner validation (no network calls)."""

import asyncio

from procurement_ai.config.settings import get_settings
from procurement_ai.graph.nodes.intent import intent_classifier_node
from procurement_ai.graph.nodes.planner import planner_node
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

    def test_agent_workflow_allowed(self):
        decision = validate_decision(
            {
                "workflow": "agent",
                "intent": "analyze",
                "metric": {"name": None},
            }
        )
        assert decision is not None
        assert decision.workflow == "agent"
        assert decision.metric is None

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

    def test_list_metric(self):
        decision = validate_decision(
            {
                "workflow": "sql",
                "metric": {"name": "pending_approvals", "dimension": None},
            }
        )
        assert decision.metric == "pending_approvals"
        assert decision.dimension is None

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


class TestPlannerNode:
    def test_metric_safety_net(self):
        state = {
            "user_input": "which payment requests are pending?",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "sql"
        assert route["metric"] == "pending_payment_requests"

    def test_detail_follow_up_reuses_previous_metric(self):
        state = {
            "user_input": "list me with each of them detailed as a table",
            "history": [],
            "previous_route": {
                "workflow": "sql",
                "intent": "analyze",
                "metric": "pending_approvals",
                "dimension": None,
                "days": None,
            },
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "sql"
        assert route["metric"] == "pending_approvals"
        assert route["follow_up"] is True

    def test_spending_change_routes_to_agent(self):
        state = {
            "user_input": "What changed in spending from 2024 to 2025?",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "agent"
        assert route["metric"] is None

    def test_vendor_most_overdue_routes_to_agent(self):
        state = {
            "user_input": "Which vendors have the most overdue invoices?",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "agent"

    def test_simple_metric_does_not_route_to_agent(self):
        state = {
            "user_input": "What is total spend?",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "sql"
        assert route["metric"] == "total_spend"

    def test_greeting_routes_to_agent(self):
        state = {"user_input": "hi", "history": [], "previous_route": None}
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "agent"

    def test_help_question_routes_to_agent(self):
        for question in (
            "help me",
            "Can you help me?",
            "what do you do?",
            "how can you help me with finance operations",
        ):
            state = {"user_input": question, "history": [], "previous_route": None}
            result = asyncio.run(planner_node(state))
            assert result["planned_route"]["workflow"] == "agent"

    def test_pending_fragment_routes_to_agent(self):
        state = {"user_input": "pend", "history": [], "previous_route": None}
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "agent"

    def test_natural_unclassified_question_routes_to_agent(self):
        state = {"user_input": "how are we doing?", "history": [], "previous_route": None}
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "agent"

    def test_pending_all_followup_routes_to_agent(self):
        state = {
            "user_input": "all",
            "history": [],
            "previous_route": {
                "workflow": "clarification",
                "clarification_message": (
                    "Do you mean pending approvals, pending payment requests, or pending payments?"
                ),
            },
        }
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "agent"

    def test_multi_pending_question_routes_to_agent(self):
        state = {
            "user_input": "show pending payments and approvals",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "agent"

    def test_policy_question_does_not_become_overdue_metric(self):
        state = {
            "user_input": "overdue policies",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "agent"
        assert route["metric"] is None

    def test_pending_payments_uses_payments_metric(self):
        state = {
            "user_input": "show pending payments",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route is not None
        assert route["workflow"] == "sql"
        assert route["metric"] == "pending_payments"

    def test_agent_first_routes_readonly_to_agent(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "orchestration_mode", "agent_first")
        monkeypatch.setattr(settings, "opencode_go_api_key", "test-key")
        state = {
            "user_input": "what anomalies and exceptions do we have?",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        route = result["planned_route"]
        assert route["workflow"] == "agent"
        assert result["planner_audit"]["planner_mode"] == "agent_first"

    def test_agent_first_keeps_actions_deterministic(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "orchestration_mode", "agent_first")
        monkeypatch.setattr(settings, "opencode_go_api_key", "test-key")
        state = {
            "user_input": "request payment for INV-000001",
            "history": [],
            "previous_route": None,
        }
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "action"

    def test_exception_category_routes_to_agent(self):
        state = {
            "user_input": "invoice exceeds po",
            "history": [],
            "previous_route": {"workflow": "detection"},
        }
        result = asyncio.run(planner_node(state))
        assert result["planned_route"]["workflow"] == "agent"

    def test_agent_followup_does_not_trigger_invoice_clarification(self):
        state = {
            "user_input": "I just said all",
            "planned_route": {
                "workflow": "agent",
                "intent": "analyze",
                "follow_up": True,
                "entity_type": None,
                "entity_id": None,
                "metric": None,
            },
            "last_invoice_number": None,
        }
        result = intent_classifier_node(state)
        assert result["workflow"] == "agent"
        assert result["clarification_needed"] is False
