from functools import lru_cache

from shared.tracing.otlp import create_otlp_tracing
from shared.tracing.reporter import OpenTelemetryTracingReporter

from ..config import get_settings


@lru_cache
def get_tracing_reporter() -> OpenTelemetryTracingReporter | None:
    """Build one optional tracing reporter per org process."""
    settings = get_settings()
    if not settings.tracing_enabled:
        return None
    return create_otlp_tracing(
        service_name="org",
        endpoint=settings.tracing_endpoint,
        sample_ratio=settings.tracing_sample_ratio,
        timeout_seconds=settings.tracing_timeout_seconds,
    )
