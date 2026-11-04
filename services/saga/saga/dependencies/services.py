from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.abstracts import SagaAbstractService
from ..services.saga_service import OnboardingSagaService
from .repositories import get_outbox_repository, get_saga_repository
from .session import SessionDependency


def get_saga_service(
    session: AsyncSession, service_type: type[SagaAbstractService] = OnboardingSagaService
) -> SagaAbstractService:
    """Build the orchestrator without opening or committing another transaction."""
    return service_type(
        saga_repository=get_saga_repository(session),
        outbox_repository=get_outbox_repository(session),
    )


def get_http_saga_service(session: SessionDependency) -> SagaAbstractService:
    """Build the same saga service for an HTTP request."""
    return get_saga_service(session)


SagaServiceDependency = Annotated[SagaAbstractService, Depends(get_http_saga_service)]
