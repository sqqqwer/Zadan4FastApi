from sqlalchemy.ext.asyncio import AsyncSession

from ..services.abstracts import SagaAbstractService
from ..services.saga_service import OnboardingSagaService
from .repositories import get_outbox_repository, get_saga_repository


def get_saga_service(
    session: AsyncSession, service_type: type[SagaAbstractService] = OnboardingSagaService
) -> SagaAbstractService:
    """Build the orchestrator without opening or committing another transaction."""
    return service_type(
        saga_repository=get_saga_repository(session),
        outbox_repository=get_outbox_repository(session),
    )
