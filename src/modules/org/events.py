import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.events.bus import AbstractEventsBus
from src.core.events.envelope import EventEnvelope
from src.core.events.types import EventType

from .dependencies.repositories import get_replica_user_repository
from .schemas.users_replica import ReplicaUserCreateScheme

logger = logging.getLogger(__name__)


async def save_user_replica(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Create or update the local user replica from an auth event.

    Args:
        envelope: Event containing the user snapshot and occurrence time.
        session: Database session shared with the inbox.
    """
    repository = get_replica_user_repository(session)
    scheme = ReplicaUserCreateScheme(
        id=envelope.payload["user_id"],
        full_name=envelope.payload["full_name"],
        company_id=envelope.payload["company_id"],
        is_active=envelope.payload["is_active"],
        last_event_at=envelope.occurred_at,
    )
    user = await repository.get_user(scheme.id)
    if user is None:
        await repository.create(scheme)
    elif scheme.last_event_at > user.last_event_at:
        user.full_name = scheme.full_name
        user.company_id = scheme.company_id
        user.is_active = scheme.is_active
        user.last_event_at = scheme.last_event_at


async def on_company_created_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Apply the company created event to the administrator replica.

    Args:
        envelope: Event data and metadata.
        session: Database session shared with the inbox.
    """
    await save_user_replica(envelope, session)
    logger.info(f"Org company.created handler event_id={envelope.event_id}")


async def on_employee_created_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Apply the employee created event to the user replica.

    Args:
        envelope: Event data and metadata.
        session: Database session shared with the inbox.
    """
    await save_user_replica(envelope, session)
    logger.info(f"Org employee.created handler event_id={envelope.event_id}")


async def on_employee_registered_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Apply the employee registered event to the user replica.

    Args:
        envelope: Event data and metadata.
        session: Database session shared with the inbox.
    """
    await save_user_replica(envelope, session)
    logger.info(f"Org employee.registered handler event_id={envelope.event_id}")


async def on_employee_email_changed_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Refresh the user replica without storing the changed email.

    Args:
        envelope: Event data and metadata.
        session: Database session shared with the inbox.
    """
    await save_user_replica(envelope, session)
    logger.info(f"Org employee.email_changed handler event_id={envelope.event_id}")


async def subscribe_handlers(bus: AbstractEventsBus) -> None:
    """Register event handlers for the org module.

    Args:
        bus: Event bus used to register handlers.
    """
    await bus.subscribe(EventType.COMPANY_CREATED, on_company_created_handler)
    await bus.subscribe(EventType.EMPLOYEE_CREATED, on_employee_created_handler)
    await bus.subscribe(EventType.EMPLOYEE_REGISTERED, on_employee_registered_handler)
    await bus.subscribe(EventType.EMPLOYEE_EMAIL_CHANGED, on_employee_email_changed_handler)
