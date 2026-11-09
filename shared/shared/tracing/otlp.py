from collections.abc import Mapping
from math import isfinite

from httpx import URL
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.util.types import AttributeValue

from .reporter import OpenTelemetryTracingReporter


def create_otlp_tracing(
    service_name: str,
    endpoint: str,
    *,
    resource_attributes: Mapping[str, AttributeValue] | None = None,
    sample_ratio: float = 1.0,
    timeout_seconds: float = 3.0,
) -> OpenTelemetryTracingReporter:
    """Build tracing with bounded background OTLP/HTTP export.

    The application supplies the service name and full traces endpoint, including
    /v1/traces. Sampling respects the parent's decision across service boundaries.
    No global provider is installed; pass this provider to instrumentation explicitly.
    """
    if not service_name.strip():
        raise ValueError("Tracing service name must not be empty")

    url = URL(endpoint)

    if not url.is_absolute_url or url.scheme not in {"http", "https"}:
        raise ValueError("Tracing endpoint must be an absolute HTTP or HTTPS URL")
    if not isfinite(sample_ratio) or not 0 <= sample_ratio <= 1:
        raise ValueError("Tracing sample ratio must be between zero and one")
    if not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("Tracing export timeout must be a positive finite value")

    attributes = dict(resource_attributes or {})
    attributes["service.name"] = service_name

    provider = TracerProvider(
        resource=Resource.create(attributes),
        sampler=ParentBased(TraceIdRatioBased(sample_ratio)),
    )
    exporter = OTLPSpanExporter(endpoint=str(url), timeout=timeout_seconds)
    provider.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=1000))

    return OpenTelemetryTracingReporter(provider)
