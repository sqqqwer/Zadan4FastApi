import logging

from src.core.events.bus import AbstractEventsBus
from src.core.events.envelope import EventEnvelope
from src.core.events.types import EventType

logger = logging.getLogger(__name__)


async def on_company_created_handler(envelope: EventEnvelope) -> None:
    """Log the company created event.

    Args:
        envelope: Event data and metadata.
    """
    logger.info(f"Tasks company.created handler event_id={envelope.event_id}")


async def on_employee_created_handler(envelope: EventEnvelope) -> None:
    """Log the employee created event.

    Args:
        envelope: Event data and metadata.
    """
    logger.info(f"Tasks employee.created handler event_id={envelope.event_id}")


async def on_employee_registered_handler(envelope: EventEnvelope) -> None:
    """Log the employee registered event.

    Args:
        envelope: Event data and metadata.
    """
    logger.info(f"Tasks employee.registered handler event_id={envelope.event_id}")


async def on_employee_email_changed_handler(envelope: EventEnvelope) -> None:
    """Log the employee email changed event.

    Args:
        envelope: Event data and metadata.
    """
    logger.info(f"Tasks employee.email_changed handler event_id={envelope.event_id}")


async def subscribe_handlers(bus: AbstractEventsBus) -> None:
    """Register event handlers for the tasks module.

    Args:
        bus: Event bus used to register handlers.
    """
    await bus.subscribe(EventType.COMPANY_CREATED, on_company_created_handler)
    await bus.subscribe(EventType.EMPLOYEE_CREATED, on_employee_created_handler)
    await bus.subscribe(EventType.EMPLOYEE_REGISTERED, on_employee_registered_handler)
    await bus.subscribe(EventType.EMPLOYEE_EMAIL_CHANGED, on_employee_email_changed_handler)
