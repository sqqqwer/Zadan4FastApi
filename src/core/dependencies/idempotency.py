import hashlib
import hmac
import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request, status
from fastapi.routing import APIRoute

from src.core.config import Settings, get_settings

from ..repositories.idempotency import IdempotencyAbstractRepository, IdempotencySqlAlchemyRepository
from ..services.idempotency import IdempotencyAbstractService, IdempotencyDBService
from .session import SessionDependency

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_declared_status_code(request: Request) -> int:
    """Get declared in router status code.

    Args:
        request: default FastApi Request class.

    Returns:
        int: declared in router status code (default is 200).
    """
    route = request.scope.get("route")

    if not isinstance(route, APIRoute):
        return status.HTTP_200_OK

    return route.status_code or status.HTTP_200_OK


DeclaredStatusCodeDependency = Annotated[int, Depends(get_declared_status_code)]


async def get_request_hash(
    request: Request,
    settings: SettingsDependency,
) -> str:
    """Get hashed request, url-endpoint and http method.

    Args:
        request: default FastApi Request class.
        settings: Application settings.

    Returns:
        str: hashed request, url-endpoint and http method.
    """
    raw_body = await request.body()

    if not raw_body:
        normalized_body = b""
    else:
        try:
            body = json.loads(raw_body)

            normalized_body = json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")

        except (json.JSONDecodeError, ValueError):
            normalized_body = raw_body

    request_data = b"\n".join(
        (
            request.method.encode("utf-8"),
            request.url.path.encode("utf-8"),
            normalized_body,
        )
    )
    secret = settings.idempotency_hmac_secret.get_secret_value().encode()

    return hmac.new(
        key=secret,
        msg=request_data,
        digestmod=hashlib.sha256,
    ).hexdigest()


HashedRequestDependency = Annotated[str, Depends(get_request_hash)]


def get_idempotency_key(key: Annotated[UUID, Header(alias="Idempotency-Key")]) -> UUID:
    """Get Idempotency key from header.

    Args:
        key: wait Key from "Idempotency-Key" header.

    Returns:
        UUID: Idempotency key.
    """
    return key


IdempotencyKeyDependency = Annotated[UUID, Depends(get_idempotency_key)]


def get_idempotency_repository(session: SessionDependency) -> IdempotencyAbstractRepository:
    """Get the idempotency repository.

    Args:
        session: Database session used by the idempotency repository.

    Returns:
        IdempotencyAbstractRepository: Idempotency repository.
    """
    return IdempotencySqlAlchemyRepository(session=session)


IdempotencyRepositoryDependency = Annotated[IdempotencyAbstractRepository, Depends(get_idempotency_repository)]


def get_idempotency_service(
    idempotency_repository: IdempotencyRepositoryDependency,
    idempotency_key: IdempotencyKeyDependency,
    status_code: DeclaredStatusCodeDependency,
    hashed_request: HashedRequestDependency,
) -> IdempotencyAbstractService:
    """Get the idempotency service.

    Args:
        idempotency_repository: Database repository for idempotency objects.
        idempotency_key: Idempotency key from the request header.
        status_code: Status code declared in the router.
        hashed_request: Hash of the request body, URL path, and HTTP method.

    Returns:
        IdempotencyAbstractService: Idempotency service.
    """
    return IdempotencyDBService(
        idempotency_repository=idempotency_repository,
        idempotency_key=idempotency_key,
        status_code=status_code,
        hashed_request=hashed_request,
    )


IdempotencyServiceDependency = Annotated[IdempotencyAbstractService, Depends(get_idempotency_service)]
