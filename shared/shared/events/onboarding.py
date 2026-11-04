import logging
from datetime import UTC, datetime
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel

from shared.outbox.repository import OutboxAbstractRepository

from .envelope import EventEnvelope
from .types import EventType

logger = logging.getLogger(__name__)


class OnboardingCommand(BaseModel):
    """Employee onboarding identifiers shared by the orchestrator and participants."""

    saga_id: UUID
    saga_type: Literal["employee_onboarding"] = "employee_onboarding"
    user_id: UUID
    company_id: UUID
    invite_id: UUID
    position_id: UUID
    struct_id: UUID

    @classmethod
    def from_envelope(cls, envelope: EventEnvelope) -> Self:
        """Validate the command before any participant changes its database."""
        if envelope.producer != "saga" or envelope.schema_version != 1:
            raise ValueError("Onboarding commands require producer=saga and schema_version=1")
        command = cls.model_validate(envelope.payload)
        if envelope.aggregate_id != command.saga_id:
            raise ValueError("Onboarding command aggregate_id must equal saga_id")
        return command


async def reply_to_saga(
    outbox: OutboxAbstractRepository,
    source: EventEnvelope,
    event_type: EventType,
    *,
    reason: str | None = None,
    resource_id: UUID | None = None,
) -> None:
    """Save one correlated result per saga and result type in the caller's transaction."""
    payload = {"saga_id": str(source.aggregate_id), "saga_type": "employee_onboarding"}
    if reason is not None:
        payload["reason"] = reason
    if resource_id is not None:
        payload["resource_id"] = str(resource_id)
    result = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        aggregate_id=source.aggregate_id,
        occurred_at=datetime.now(UTC),
        correlation_id=source.correlation_id,
        causation_id=source.event_id,
        producer=event_type.value.split(".", maxsplit=1)[0],
        payload=payload,
    )
    await outbox.add_once(result, dedup_key=f"saga:{source.aggregate_id}:{event_type.value}")
    logger.info(
        "Onboarding result queued: saga_id=%s event_type=%s reason=%s correlation_id=%s",
        source.aggregate_id,
        event_type,
        reason,
        source.correlation_id,
    )
