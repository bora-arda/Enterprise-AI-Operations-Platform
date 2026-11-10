"""Tests for application-level access scope."""

import asyncio

from procurement_ai.agent.tools import execute_tool
from procurement_ai.config.settings import get_settings
from procurement_ai.security.access import build_access_scope, scope_from_state


class TestAccessScope:
    def test_specialist_is_restricted_when_enabled(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "row_level_access_enabled", True)
        monkeypatch.setattr(settings, "row_level_global_roles", "manager,finance,director,admin")
        scope = build_access_scope("u1", "specialist", "dept-1")
        assert scope.restricted is True
        assert scope.allows_department("dept-1") is True
        assert scope.allows_department("dept-2") is False

    def test_manager_is_global(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "row_level_access_enabled", True)
        monkeypatch.setattr(settings, "row_level_global_roles", "manager,finance,director,admin")
        scope = build_access_scope("u2", "manager", "dept-1")
        assert scope.restricted is False
        assert scope.allows_department("dept-2") is True

    def test_scope_can_be_disabled_for_tests(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "row_level_access_enabled", True)
        scope = build_access_scope("u1", "specialist", "dept-1", enabled=False)
        assert scope.restricted is False

    def test_scope_from_state(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "row_level_access_enabled", True)
        monkeypatch.setattr(settings, "row_level_global_roles", "manager")
        scope = scope_from_state({"user_id": "u1", "user_role": "specialist", "department_id": "dept-1"})
        assert scope.user_id == "u1"
        assert scope.restricted is True

    def test_restricted_sql_is_denied_before_database(self):
        scope = build_access_scope("u1", "specialist", "dept-1", enabled=True)
        result = asyncio.run(
            execute_tool(
                "query_database",
                {"sql": "SELECT 1"},
                scope=scope,
            )
        )
        assert result["error"] == "access_denied"
