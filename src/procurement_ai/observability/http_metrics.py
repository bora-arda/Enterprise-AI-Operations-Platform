"""HTTP metrics middleware for Prometheus."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from procurement_ai.observability.metrics import REQUEST_COUNT, REQUEST_DURATION

logger = logging.getLogger(__name__)

_BUCKETS = {
    "/chat": "/chat",
    "/approvals": "/approvals",
    "/anomalies": "/anomalies",
    "/health": "/health",
    "/metrics": "/metrics",
    "/docs": "/docs",
    "/openapi.json": "/openapi.json",
    "/": "/",
}


def _bucket(path: str) -> str:
    if path in _BUCKETS:
        return _BUCKETS[path]
    if path.startswith("/approvals/"):
        return "/approvals/{id}"
    return "other"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request count and latency by path bucket."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        bucket = _bucket(request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            REQUEST_COUNT.labels(intent="exception", workflow=bucket).inc()
            raise
        duration = time.perf_counter() - start

        REQUEST_COUNT.labels(intent=request.method, workflow=bucket).inc()
        REQUEST_DURATION.labels(intent=bucket).observe(duration)
        return response
