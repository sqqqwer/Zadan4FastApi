from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from .types import EventType


class EventEnvelope(BaseModel):
    """Event data and metadata."""

    event_id: UUID
    event_type: EventType
    aggregate_id: UUID
    occurred_at: datetime
    schema_version: int = 1
    correlation_id: UUID
    causation_id: UUID | None = None
    producer: str
    payload: dict[str, Any]
