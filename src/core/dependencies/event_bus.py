from typing import Annotated

from fastapi import Depends, Request

from src.core.events.bus import AbstractEventsBus


def get_event_bus(request: Request) -> AbstractEventsBus:
    """Get the event bus.

    Args:
        request: FastAPI request object.

    Returns:
        AbstractEventsBus: Event bus stored in request.app.state and set in lifespan().
    """
    return request.app.state.event_bus


EventBusDependency = Annotated[AbstractEventsBus, Depends(get_event_bus)]
