from collections.abc import Sequence

from fastapi import FastAPI
from httpx import AsyncClient, Client
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from .reporter import OpenTelemetryTracingReporter


def instrument_app(app: FastAPI, tracing: OpenTelemetryTracingReporter, *, excluded_urls: str = "") -> None:
    """Trace API requests with application-supplied URL exclusions before startup."""
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracing.provider,
        excluded_urls=excluded_urls,
        exclude_spans=["receive", "send"],
    )


def instrument_http_client(client: Client | AsyncClient, tracing: OpenTelemetryTracingReporter) -> None:
    """Trace one HTTP client and forward context without patching other clients."""
    HTTPXClientInstrumentor.instrument_client(client, tracer_provider=tracing.provider)


def instrument_databases(
    engines: Sequence[Engine | AsyncEngine],
    tracing: OpenTelemetryTracingReporter,
) -> None:
    """Trace the process's engines in one call before their first use."""
    SQLAlchemyInstrumentor().instrument(
        engines=[engine.sync_engine if isinstance(engine, AsyncEngine) else engine for engine in engines],
        tracer_provider=tracing.provider,
    )
