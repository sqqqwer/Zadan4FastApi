from datetime import UTC, datetime
from uuid import uuid4

from shared.events.envelope import EventEnvelope
from shared.events.onboarding import OnboardingCommand, reply_to_saga
from shared.events.types import EventType
from shared.outbox.repository import OutboxAbstractRepository

from ..repositories.onboarding import OnboardingRepository
from .constants import EVENT_PRODUCER


class OnboardingService:
    """Create or cancel a welcome task without committing the inbox transaction."""

    def __init__(self, repository: OnboardingRepository, outbox_repository: OutboxAbstractRepository) -> None:
        """Use repositories bound to the same session as the inbox."""
        self.repository = repository
        self.outbox_repository = outbox_repository

    async def create_welcome_task(self, envelope: EventEnvelope) -> None:
        """Create at most one task and refuse late creation after cancellation."""
        command = OnboardingCommand.from_envelope(envelope)
        record = await self.repository.get_or_create(command)
        if record.cancelled:
            await reply_to_saga(
                self.outbox_repository,
                envelope,
                EventType.TASKS_WELCOME_TASK_CREATION_FAILED,
                reason="onboarding_cancelled",
            )
            return
        if record.task_id is None:
            await self.repository.create_task(record, command)
        await reply_to_saga(
            self.outbox_repository, envelope, EventType.TASKS_WELCOME_TASK_CREATED, resource_id=record.task_id
        )

    async def cancel_welcome_task(self, envelope: EventEnvelope) -> None:
        """Persist cancellation even if the task was never created or has been deleted."""
        command = OnboardingCommand.from_envelope(envelope)
        record = await self.repository.get_or_create(command)
        changed = await self.repository.cancel_task(record)
        if changed is not None:
            task, old_status = changed
            result = EventEnvelope(
                event_id=uuid4(),
                event_type=EventType.TASK_STATUS_CHANGED,
                aggregate_id=task.id,
                occurred_at=datetime.now(UTC),
                correlation_id=envelope.correlation_id,
                causation_id=envelope.event_id,
                producer=EVENT_PRODUCER,
                payload={
                    "task_id": task.id,
                    "task_author_id": task.author_id,
                    "user_changed_state_id": command.user_id,
                    "old_status": old_status.value,
                    "new_status": task.status.value,
                    "new_status_version": task.status_version,
                },
            )
            await self.outbox_repository.add(result, dedup_key=f"task.status_changed:{task.id}:{task.status_version}")
        await reply_to_saga(self.outbox_repository, envelope, EventType.TASKS_WELCOME_TASK_CANCELLED)
