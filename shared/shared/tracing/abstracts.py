from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextlib import AbstractContextManager

from opentelemetry.trace import Span, SpanKind
from opentelemetry.util.types import AttributeValue


class TracingAbstractReporter(ABC):
    """Tracing operations used independently of the exporter and storage."""

    @abstractmethod
    def span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Mapping[str, AttributeValue] | None = None,
        carrier: Mapping[str, str] | None = None,
    ) -> AbstractContextManager[Span]:
        """Trace an operation under the current or explicitly received context."""
        ...

    @abstractmethod
    def inject_context(self) -> dict[str, str]:
        """Serialize the current trace context for storage or transport."""
        ...
