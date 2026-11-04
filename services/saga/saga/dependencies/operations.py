from typing import Annotated

from fastapi import Depends

from shared.operations.repository import OperationsSqlAlchemyRepository
from shared.operations.service import OperationsService

from ..config import get_settings
from ..models.outbox_messages import OutboxMessagesSaga
from ..services.constants import CONSUMER_NAME
from .session import SessionDependency


def get_operations_service(session: SessionDependency) -> OperationsService:
    """Build operational checks using the saga service's request session."""
    repository = OperationsSqlAlchemyRepository(session=session, model=OutboxMessagesSaga)
    return OperationsService(
        repository=repository,
        kafka_bootstrap_servers=get_settings().kafka_bootstrap_servers,
        consumer_name=CONSUMER_NAME,
        consumer_topics=("auth.events", "org.events", "tasks.events"),
    )


OperationsServiceDependency = Annotated[OperationsService, Depends(get_operations_service)]
