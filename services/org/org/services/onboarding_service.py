from shared.events.envelope import EventEnvelope
from shared.events.onboarding import OnboardingCommand, reply_to_saga
from shared.events.types import EventType
from shared.outbox.repository import OutboxAbstractRepository

from ..repositories.onboarding import OnboardingRepository


class OnboardingService:
    """Handle employee assignment and its idempotent compensation."""

    def __init__(self, repository: OnboardingRepository, outbox_repository: OutboxAbstractRepository) -> None:
        """Keep business changes and replies in the caller's transaction."""
        self.repository = repository
        self.outbox_repository = outbox_repository

    async def assign_employee(self, envelope: EventEnvelope) -> None:
        """Apply an assignment once and repeat its durable result on duplicate commands."""
        command = OnboardingCommand.from_envelope(envelope)
        record = await self.repository.get_or_create(command)
        if not record.cancelled and record.binding_id is None and record.failure_reason is None:
            record.failure_reason = await self.repository.assign(record, command)
        reason = "onboarding_cancelled" if record.cancelled else record.failure_reason
        event_type = EventType.ORG_EMPLOYEE_ASSIGNMENT_FAILED if reason else EventType.ORG_EMPLOYEE_ASSIGNED
        await reply_to_saga(self.outbox_repository, envelope, event_type, reason=reason, resource_id=record.binding_id)

    async def unassign_employee(self, envelope: EventEnvelope) -> None:
        """Confirm compensation even if assignment never happened or was already removed."""
        command = OnboardingCommand.from_envelope(envelope)
        record = await self.repository.get_or_create(command)
        await self.repository.unassign(record)
        await reply_to_saga(self.outbox_repository, envelope, EventType.ORG_EMPLOYEE_UNASSIGNED)
