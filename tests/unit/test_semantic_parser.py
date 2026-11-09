"""Unit tests for semantic metric parsing and formatting."""

from procurement_ai.semantic.metrics import MetricResult
from procurement_ai.semantic.parser import format_metric_result, parse_metric_request


class TestMetricParser:
    def test_spend_by_category(self):
        req = parse_metric_request("Show me spending by category")
        assert req is not None
        assert req.metric == "total_spend"
        assert req.dimension == "category"

    def test_spend_by_department(self):
        req = parse_metric_request("What is total spend by department?")
        assert req.metric == "total_spend"
        assert req.dimension == "department"

    def test_exception_rate_by_vendor(self):
        req = parse_metric_request("What is the exception rate by vendor?")
        assert req.metric == "exception_rate"
        assert req.dimension == "vendor"

    def test_most_exceptions_defaults_to_vendor(self):
        req = parse_metric_request("Which vendors have the most exceptions?")
        assert req.metric == "exception_count"
        assert req.dimension == "vendor"

    def test_overdue_rate(self):
        req = parse_metric_request("What is the overdue rate by vendor?")
        assert req.metric == "overdue_rate"
        assert req.dimension == "vendor"

    def test_average_invoice_value(self):
        req = parse_metric_request("What is the average invoice value?")
        assert req.metric == "avg_invoice_value"

    def test_approval_cycle_time(self):
        req = parse_metric_request("What is the average approval cycle time by department?")
        assert req.metric == "approval_cycle_time"
        assert req.dimension == "department"

    def test_contracts_expiring_days(self):
        req = parse_metric_request("Which contracts expire within 60 days?")
        assert req.metric == "contracts_expiring"
        assert req.days == 60

    def test_contracts_expiring_default_days(self):
        req = parse_metric_request("Which contracts are expiring?")
        assert req.metric == "contracts_expiring"
        assert req.days == 60

    def test_last_quarter_days(self):
        req = parse_metric_request("Show spending by month for the last quarter")
        assert req.days == 90

    def test_overdue_invoices_list(self):
        req = parse_metric_request("Which invoices are overdue?")
        assert req.metric == "overdue_invoices"
        assert req.dimension is None

    def test_pending_payment_requests(self):
        req = parse_metric_request("which payment requests are pending?")
        assert req.metric == "pending_payment_requests"

    def test_pending_approvals(self):
        req = parse_metric_request("list me all pending payments and approvals")
        assert req.metric == "pending_approvals"

    def test_pending_payments(self):
        req = parse_metric_request("show pending payments")
        assert req.metric == "pending_payment_requests"

    def test_non_metric_question(self):
        assert parse_metric_request("Why is invoice INV-000001 overdue?") is None
        assert parse_metric_request("Find duplicate invoices") is None


class TestMetricFormatting:
    def test_currency(self):
        result = MetricResult(
            metric="total_spend",
            label="Total spend",
            dimension="category",
            rows=[{"label": "IT", "value": 1234.5}],
        )
        text = format_metric_result(result)
        assert "GBP 1,234.50" in text

    def test_rate(self):
        result = MetricResult(
            metric="overdue_rate",
            label="Overdue rate",
            dimension="vendor",
            rows=[{"label": "Acme", "value": 12.345}],
        )
        assert "12.35%" in format_metric_result(result)

    def test_expiring(self):
        result = MetricResult(
            metric="contracts_expiring",
            label="Contracts expiring",
            dimension=None,
            rows=[
                {
                    "label": "CF-2022-00001",
                    "detail": "Retrofit Guide",
                    "end_date": "2026-12-01",
                    "vendor": "Acme",
                }
            ],
        )
        text = format_metric_result(result)
        assert "CF-2022-00001" in text
        assert "2026-12-01" in text

    def test_pending_approvals_table(self):
        result = MetricResult(
            metric="pending_approvals",
            label="Pending approvals",
            dimension=None,
            rows=[
                {
                    "Approval": "APPR-1",
                    "Type": "payment_request",
                    "Invoice": "INV-1",
                    "Amount": 100,
                    "Currency": "GBP",
                }
            ],
        )
        text = format_metric_result(result)
        assert "| Approval |" in text
        assert "APPR-1" in text
        assert "payment_request" in text
