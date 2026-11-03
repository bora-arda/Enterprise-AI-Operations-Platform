"""Unit tests for HTTP metrics path bucketing."""

from procurement_ai.observability.http_metrics import _bucket


class TestPathBucket:
    def test_exact_paths(self):
        assert _bucket("/chat") == "/chat"
        assert _bucket("/approvals") == "/approvals"
        assert _bucket("/anomalies") == "/anomalies"
        assert _bucket("/health") == "/health"

    def test_approval_detail_paths(self):
        assert _bucket("/approvals/abc-123/decide") == "/approvals/{id}"

    def test_unknown_path(self):
        assert _bucket("/something/else") == "other"
