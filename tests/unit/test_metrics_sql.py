"""Unit tests for governed metric SQL construction (no database required)."""

from procurement_ai.semantic.metrics import MetricRequest, _build_sql


class TestMetricSql:
    def test_no_dimension_uses_ordinal_group_by(self):
        sql, _ = _build_sql(MetricRequest(metric="total_spend"))
        assert "GROUP BY 1" in sql
        assert "GROUP BY 'total'" not in sql

    def test_dimension_group_by_uses_allowlisted_expression(self):
        sql, _ = _build_sql(MetricRequest(metric="total_spend", dimension="vendor"))
        assert "GROUP BY COALESCE(v.name, 'Unknown vendor')" in sql

    def test_metric_with_no_allowed_dimension_falls_back_to_total(self):
        sql, _ = _build_sql(MetricRequest(metric="overdue_invoices", dimension="vendor"))
        assert "GROUP BY" not in sql
        assert "i.status = 'overdue'" in sql

    def test_contracts_expiring_uses_days(self):
        sql, params = _build_sql(MetricRequest(metric="contracts_expiring", days=30))
        assert "CAST(:days AS INTEGER)" in sql
        assert params["days"] == 30
