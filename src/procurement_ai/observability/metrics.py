"""Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram, Info

# Request metrics
REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total requests by intent",
    ["intent", "workflow"],
)

WORKFLOW_COUNT = Counter(
    "agent_workflow_total",
    "Requests by routed workflow",
    ["workflow", "intent"],
)

WORKFLOW_DURATION = Histogram(
    "agent_workflow_duration_seconds",
    "End-to-end workflow duration",
    ["workflow"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

REQUEST_DURATION = Histogram(
    "agent_request_duration_seconds",
    "End-to-end request duration",
    ["intent"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

NODE_DURATION = Histogram(
    "node_duration_seconds",
    "Per-node execution duration",
    ["node"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0],
)

# LLM metrics
LLM_CALLS = Counter(
    "llm_calls_total",
    "LLM calls by provider",
    ["provider"],
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Token usage by type",
    ["type"],  # input | output | cache_read | cache_write
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
)

# Retrieval metrics
RETRIEVAL_LATENCY = Histogram(
    "retrieval_latency_seconds",
    "Retrieval pipeline latency",
    ["component"],  # bm25 | dense | fusion | rerank
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5],
)

# Tool metrics
TOOL_CALLS = Counter(
    "tool_calls_total",
    "Tool calls by name",
    ["tool"],
)

TOOL_ERRORS = Counter(
    "tool_errors_total",
    "Tool errors by name",
    ["tool"],
)

# Business metrics
APPROVAL_REQUESTS = Counter(
    "approval_requests_total",
    "Approvals by status",
    ["status"],
)

ANOMALIES_DETECTED = Counter(
    "anomalies_detected_total",
    "Anomalies by type (deterministic detection workflow)",
    ["type"],
)

EXCEPTIONS_OPEN = Gauge(
    "exceptions_open_total",
    "Open exception records by type (agent list_exceptions view)",
    ["type"],
)

# System info
APP_INFO = Info(
    "app_info",
    "Application information",
)
