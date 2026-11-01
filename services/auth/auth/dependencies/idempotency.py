from typing import Annotated

from fastapi import Depends
from pydantic import SecretStr
from shared.idempotency.dependencies import make_idempotency_service_dependency
from shared.idempotency.repository import IdempotencyAbstractRepository, IdempotencySqlAlchemyRepository
from shared.idempotency.service import IdempotencyAbstractService

from ..config import get_settings
from ..models.idempotency import IdempotencyAuth
from .session import SessionDependency


def get_idempotency_secret() -> SecretStr:
    """Read the HMAC secret from this service's settings."""
    return get_settings().idempotency_hmac_secret


def get_idempotency_repository(session: SessionDependency) -> IdempotencyAbstractRepository:
    """Build the repository using the local table and request session."""
    return IdempotencySqlAlchemyRepository(session=session, model=IdempotencyAuth)


get_idempotency_service = make_idempotency_service_dependency(
    repository_dependency=get_idempotency_repository,
    secret_dependency=get_idempotency_secret,
)

IdempotencyServiceDependency = Annotated[IdempotencyAbstractService, Depends(get_idempotency_service)]
