"""Parse natural-language metric requests into governed metric calls."""

import re

from procurement_ai.semantic.metrics import MetricRequest


def _detect_metric(q: str) -> str | None:
    if re.search(r"\bexception\s+rate\b", q):
        return "exception_rate"
    if re.search(r"\b(most|top|highest|count|number of)\b.*\bexceptions?\b", q) or re.search(
        r"\bexceptions?\b.*\b(by|per)\s+vendor", q
    ):
        return "exception_count"
    if re.search(r"\boverdue\s+rate\b|\bpercentage\b.*\boverdue\b", q):
        return "overdue_rate"
    if re.search(r"\baverage\s+invoice\b|\bavg\s+invoice\b", q):
        return "avg_invoice_value"
    if re.search(r"\bhow\s+many\s+invoices\b|\binvoice\s+count\b", q):
        return "invoice_count"
    if re.search(r"\bapproval\s+cycle\b|\btime\s+to\s+approve\b|\baverage\s+approval\b", q):
        return "approval_cycle_time"
    if re.search(r"\b(expire|expiring|expiration)\b", q):
        return "contracts_expiring"
    if re.search(r"\bspend(ing)?\b|\bcost\b|\btotal\s+value\b", q):
        return "total_spend"
    return None


def _detect_dimension(q: str) -> str | None:
    if re.search(r"\b(by|per)\s+vendor\b|\bwhich\s+vendors?\b|\btop\s+vendors?\b", q):
        return "vendor"
    if re.search(r"\b(by|per)\s+category\b|\bcategories\b", q):
        return "category"
    if re.search(r"\b(by|per)\s+department\b|\bdepartments?\b", q):
        return "department"
    if re.search(r"\b(by|per)\s+month\b|\bmonthly\b", q):
        return "month"
    if re.search(r"\b(by|per)\s+status\b", q):
        return "status"
    if re.search(r"\bexception\s+type\b", q):
        return "exception_type"
    return None


def _detect_days(q: str) -> int | None:
    match = re.search(r"\b(?:last|past|next|within|in\s+the\s+last)\s+(\d{1,3})\s+days?\b", q)
    if match:
        return int(match.group(1))
    if re.search(r"\blast\s+quarter\b", q):
        return 90
    if re.search(r"\blast\s+year\b", q):
        return 365
    return None


def parse_metric_request(question: str) -> MetricRequest | None:
    """Return a governed metric request, or None if this is not an analytics question."""
    q = question.lower().strip()
    metric = _detect_metric(q)
    if not metric:
        return None

    dimension = _detect_dimension(q)

    # Sensible defaults
    if dimension is None and metric in ("exception_count", "exception_rate"):
        dimension = "vendor"
    if metric == "contracts_expiring":
        dimension = None

    days = _detect_days(q)
    if metric == "contracts_expiring":
        days = days or 60

    return MetricRequest(metric=metric, dimension=dimension, days=days, limit=10)


def format_metric_result(result) -> str:
    """Format a MetricResult for the user with explicit units."""
    if not result.rows:
        return f"{result.label}: no data matched the request."

    metric = result.metric
    lines = [f"{result.label}:"]

    for row in result.rows:
        label = row.get("label")
        value = row.get("value")

        if metric == "contracts_expiring":
            lines.append(
                f"- {row.get('label')} — {row.get('detail')} (ends {row.get('end_date')}, vendor: {row.get('vendor')})"
            )
            continue

        if metric in ("overdue_rate", "exception_rate"):
            formatted = f"{float(value):.2f}%"
        elif metric == "approval_cycle_time":
            formatted = f"{float(value):.1f} hours"
        elif metric in ("invoice_count", "exception_count"):
            formatted = f"{int(value):,}"
        else:
            formatted = f"GBP {float(value):,.2f}"

        lines.append(f"- {label}: {formatted}")

    return "\n".join(lines)
