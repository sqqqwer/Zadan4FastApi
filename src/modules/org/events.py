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
    logger.info(f"Org company.created handler event_id={envelope.event_id}")


async def on_employee_email_changed_handler(envelope: EventEnvelope) -> None:
    """Log the employee email changed event.

    Args:
        envelope: Event data and metadata.
    """
    logger.info(f"Org employee.email_changed handler event_id={envelope.event_id}")


async def subscribe_handlers(bus: AbstractEventsBus) -> None:
    """Register event handlers for the org module.

    Args:
        bus: Event bus used to register handlers.
    """
    await bus.subscribe(EventType.COMPANY_CREATED, on_company_created_handler)
    await bus.subscribe(EventType.EMPLOYEE_EMAIL_CHANGED, on_employee_email_changed_handler)
