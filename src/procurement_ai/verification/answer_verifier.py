"""Answer verification.

This is a deterministic consistency check, not a replacement for business
validation. It flags numbers that do not appear in tool evidence and missing or
weak citations. Verification warnings reduce confidence but do not silently
rewrite the answer.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from procurement_ai.observability.metrics import ANSWER_VERIFICATION

NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d+)?")
CURRENCY_RE = re.compile(r"(?:£|\bGBP\b|\bEUR\b|\bUSD\b|€|\$)\s?([-+]?\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
PERCENT_RE = re.compile(r"([-+]?\d[\d,]*(?:\.\d+)?)\s?%")


@dataclass
class VerificationResult:
    status: str
    checked_numbers: int = 0
    unsupported_numbers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checked_numbers": self.checked_numbers,
            "unsupported_numbers": self.unsupported_numbers[:20],
            "warnings": self.warnings,
        }


def _numeric_values(text: str) -> set[float]:
    values: set[float] = set()
    for raw in NUMBER_RE.findall(text or ""):
        try:
            values.add(float(raw.replace(",", "")))
        except ValueError:
            continue
    return values


def _numeric_claims(answer: str) -> list[str]:
    claims = CURRENCY_RE.findall(answer or "")
    claims.extend(PERCENT_RE.findall(answer or ""))
    # Ignore tiny bare counts and years; monetary/percent claims are the
    # financially material checks.
    return claims


def verify_answer(
    answer: str,
    evidence: list[Any],
    citations: list[dict],
    *,
    tool_errors: int = 0,
    had_truncated_output: bool = False,
) -> VerificationResult:
    """Check numeric support and evidence coverage for a final answer."""
    if not answer.strip():
        result = VerificationResult(status="failed", warnings=["empty answer"])
        ANSWER_VERIFICATION.labels(status=result.status).inc()
        return result

    evidence_text = "\n".join(item if isinstance(item, str) else json.dumps(item, default=str) for item in evidence)
    evidence_numbers = _numeric_values(evidence_text)
    claims = _numeric_claims(answer)
    warnings: list[str] = []
    unsupported: list[str] = []

    if tool_errors:
        warnings.append(f"{tool_errors} tool call(s) failed")
    if had_truncated_output:
        warnings.append("tool output was truncated; totals may be incomplete")

    for raw in claims:
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        if not evidence_numbers:
            unsupported.append(raw)
            continue
        tolerance = max(abs(value) * 0.01, 0.01)
        if not any(abs(value - candidate) <= tolerance for candidate in evidence_numbers):
            unsupported.append(raw)

    checked = len(claims) if claims else 0

    if unsupported:
        warnings.append("Some numeric claims were not found in tool evidence: " + ", ".join(unsupported[:8]))
    if not citations and evidence:
        warnings.append("data evidence was used without citations")

    status = "passed" if not warnings else "warnings"
    result = VerificationResult(
        status=status,
        checked_numbers=checked,
        unsupported_numbers=unsupported,
        warnings=warnings,
    )
    ANSWER_VERIFICATION.labels(status=status).inc()
    return result
