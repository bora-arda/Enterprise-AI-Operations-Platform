"""OpenTelemetry tracing setup."""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from procurement_ai.config.settings import get_settings

logger = logging.getLogger(__name__)

_tracer: trace.Tracer | None = None


def setup_tracing() -> trace.Tracer | None:
    """Setup OpenTelemetry tracing."""
    settings = get_settings()

    try:
        resource = Resource.create({"service.name": "procurement-ai-platform"})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(__name__)
        logger.info("OpenTelemetry tracing initialized")
        return _tracer
    except Exception as e:
        logger.warning(f"Failed to setup tracing: {e}")
        return None


def get_tracer() -> trace.Tracer | None:
    """Get the tracer instance."""
    return _tracer
