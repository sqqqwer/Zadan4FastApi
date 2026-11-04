from sqlalchemy.ext.asyncio import AsyncSession

from shared.outbox.repository import OutboxAbstractRepository, OutboxSqlAlchemyRepository

from ..models.outbox_messages import OutboxMessagesSaga
from ..repositories.abstracts import SagaAbstractRepository
from ..repositories.sqlalchemy_repositories import SagaSqlAlchemyRepository


def get_saga_repository(session: AsyncSession) -> SagaAbstractRepository:
    """Build the saga repository using the consumer's current session."""
    return SagaSqlAlchemyRepository(session)


def get_outbox_repository(session: AsyncSession) -> OutboxAbstractRepository:
    """Build the saga outbox repository using the same session."""
    return OutboxSqlAlchemyRepository(session, model=OutboxMessagesSaga)
