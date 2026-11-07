import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.bus import AbstractEventsBus
from shared.events.envelope import EventEnvelope
from shared.events.types import EventType

logger = logging.getLogger(__name__)


async def on_employee_registered_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Log the employee registration notification."""
    payload = envelope.payload
    logger.info(
        f"Notification employee.registered: user_id={payload['user_id']} "
        f"full_name={payload['full_name']} event_id={envelope.event_id}"
    )


async def on_task_status_changed_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Log the task status notification."""
    payload = envelope.payload
    logger.info(
        f"Notification task.status_changed: task_id={payload['task_id']} "
        f"task_author_id={payload['task_author_id']} "
        f"old_status={payload['old_status']} new_status={payload['new_status']} "
        f"event_id={envelope.event_id}"
    )


async def on_employee_email_changed_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Log the employee email notification."""
    payload = envelope.payload
    logger.info(
        f"Notification employee.email_changed: user_id={payload['user_id']} "
        f"new_email={payload['new_email']} event_id={envelope.event_id}"
    )


async def subscribe_handlers(bus: AbstractEventsBus) -> None:
    """Register notification handlers."""
    await bus.subscribe(EventType.EMPLOYEE_REGISTERED, on_employee_registered_handler)
    await bus.subscribe(EventType.TASK_STATUS_CHANGED, on_task_status_changed_handler)
    await bus.subscribe(EventType.EMPLOYEE_EMAIL_CHANGED, on_employee_email_changed_handler)
