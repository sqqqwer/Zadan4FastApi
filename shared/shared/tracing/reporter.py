import asyncio
from collections.abc import AsyncGenerator, Generator, Mapping
from contextlib import asynccontextmanager, contextmanager
from typing import override

from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.util.types import AttributeValue

from .abstracts import TracingAbstractReporter


class OpenTelemetryTracingReporter(TracingAbstractReporter):
    """Create spans and propagate W3C trace context using an injected provider."""

    def __init__(self, provider: TracerProvider) -> None:
        """Take ownership of a provider configured by the application."""
        self.provider = provider
        self.tracer = provider.get_tracer("shared.tracing")
        self.propagator = TraceContextTextMapPropagator()

    @override
    @contextmanager
    def span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Mapping[str, AttributeValue] | None = None,
        carrier: Mapping[str, str] | None = None,
    ) -> Generator[Span]:
        """Record duration and uncaught errors, then restore the previous context.

        An omitted carrier uses the active span. An explicit carrier, including
        an empty mapping, starts from the received context instead. This prevents
        unrelated messages from inheriting a worker's ambient span.
        """
        context = self.propagator.extract(dict(carrier), context=Context()) if carrier is not None else None
        with self.tracer.start_as_current_span(name, context=context, kind=kind, attributes=attributes) as span:
            yield span

    @override
    def inject_context(self) -> dict[str, str]:
        """Copy only traceparent and tracestate without request data or baggage."""
        carrier: dict[str, str] = {}
        self.propagator.inject(carrier)
        return carrier

    @asynccontextmanager
    async def running(self) -> AsyncGenerator[None]:
        """Finish background exports on exit without blocking the event loop."""
        try:
            yield
        finally:
            await asyncio.to_thread(self.provider.shutdown)
