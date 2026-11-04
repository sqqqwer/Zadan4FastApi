from typing import Annotated

from fastapi import Depends

from shared.operations.repository import OperationsSqlAlchemyRepository
from shared.operations.service import OperationsService

from ..config import get_settings
from ..models.outbox_messages import OutboxMessagesAuth
from .session import SessionDependency


def get_operations_service(session: SessionDependency) -> OperationsService:
    """Build operational checks using this service's request session."""
    repository = OperationsSqlAlchemyRepository(session=session, model=OutboxMessagesAuth)
    return OperationsService(
        repository=repository,
        kafka_bootstrap_servers=get_settings().kafka_bootstrap_servers,
        consumer_name="tasks-platform.auth",
    )


OperationsServiceDependency = Annotated[OperationsService, Depends(get_operations_service)]
