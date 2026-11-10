"""Tests for deterministic answer verification (no LLM/database required)."""

from procurement_ai.verification.answer_verifier import verify_answer


class TestAnswerVerification:
    def test_supported_currency_passes(self):
        result = verify_answer(
            "Total spend was GBP 123,456.78.",
            [{"value": 123456.78, "currency": "GBP"}],
            [{"source": "metric:total_spend", "snippet": "GBP 123,456.78"}],
        )
        assert result.status == "passed"
        assert result.checked_numbers == 1

    def test_unsupported_currency_warns(self):
        result = verify_answer(
            "Total spend was GBP 999,999.99.",
            [{"value": 123456.78, "currency": "GBP"}],
            [{"source": "metric:total_spend", "snippet": "GBP 123,456.78"}],
        )
        assert result.status == "warnings"
        assert result.unsupported_numbers
        assert any("not found" in warning for warning in result.warnings)

    def test_missing_citation_warns_when_evidence_exists(self):
        result = verify_answer("Invoice INV-1 is overdue.", [{"status": "overdue"}], [])
        assert result.status == "warnings"
        assert any("without citations" in warning for warning in result.warnings)

    def test_tool_error_warns(self):
        result = verify_answer("There are 3 issues.", [{"count": 3}], [{"source": "x"}], tool_errors=1)
        assert result.status == "warnings"
        assert any("failed" in warning for warning in result.warnings)

    def test_empty_answer_fails(self):
        result = verify_answer("", [], [])
        assert result.status == "failed"
