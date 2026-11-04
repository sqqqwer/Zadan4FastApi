from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ReadinessResponse(BaseModel):
    """Availability of the HTTP service's dependencies."""

    status: Literal["ready", "not_ready"]
    database: Literal["ok", "error"]
    kafka: Literal["ok", "error"]


class PendingOutboxMessage(BaseModel):
    """Publication diagnostics without the event's business payload."""

    id: int
    event_id: UUID
    event_type: str
    correlation_id: UUID
    created_at: datetime
    attempts: int
    last_error: str | None


class PendingOutboxResponse(BaseModel):
    """Total pending count and the requested page of messages."""

    total: int
    items: list[PendingOutboxMessage]


class ConsumerPartitionLag(BaseModel):
    """Committed and available offsets for one subscribed partition."""

    topic: str
    partition: int
    committed_offset: int | None
    beginning_offset: int
    end_offset: int
    lag: int


class ConsumerLagResponse(BaseModel):
    """Consumer group lag, or an unavailable measurement when Kafka fails."""

    status: Literal["ok", "error"]
    group_id: str
    total_lag: int | None
    partitions: list[ConsumerPartitionLag]
