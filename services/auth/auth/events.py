import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.bus import AbstractEventsBus
from shared.events.envelope import EventEnvelope
from shared.events.types import EventType

from .dependencies.services import get_onboarding_service

logger = logging.getLogger(__name__)


async def on_task_status_changed_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Log the task status changed event.

    Args:
        envelope: Event data and metadata.
        session: Database session shared with the inbox.
    """
    logger.info(f"Auth task.status_changed handler event_id={envelope.event_id}")


async def on_invalidate_invite_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Invalidate an employee invite and confirm the compensation."""
    await get_onboarding_service(session).invalidate_invite(envelope)


async def subscribe_handlers(bus: AbstractEventsBus) -> None:
    """Register event handlers for the auth module.

    Args:
        bus: Event bus used to register handlers.
    """
    await bus.subscribe(EventType.TASK_STATUS_CHANGED, on_task_status_changed_handler)
    await bus.subscribe(EventType.AUTH_INVALIDATE_INVITE, on_invalidate_invite_handler)
