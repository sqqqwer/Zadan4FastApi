from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.bus import AbstractEventsBus
from shared.events.envelope import EventEnvelope
from shared.events.types import EventType

from .dependencies.services import get_saga_service
from .services.constants import RESULT_EVENTS


async def on_employee_registered_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Start onboarding in the transaction shared with the consumer's inbox."""
    await get_saga_service(session).start(envelope)


async def on_saga_result_handler(envelope: EventEnvelope, session: AsyncSession) -> None:
    """Apply a participant's reply in the same local transaction."""
    await get_saga_service(session).handle(envelope)


async def subscribe_handlers(bus: AbstractEventsBus) -> None:
    """Subscribe only to onboarding starts and participant results."""
    await bus.subscribe(EventType.EMPLOYEE_REGISTERED, on_employee_registered_handler)
    for event_type in RESULT_EVENTS:
        await bus.subscribe(event_type, on_saga_result_handler)
