import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request, status
from fastapi.routing import APIRoute
from pydantic import SecretStr

from .repository import IdempotencyAbstractRepository
from .service import IdempotencyAbstractService, IdempotencyDBService


def _get_declared_status_code(request: Request) -> int:
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


DeclaredStatusCodeDependency = Annotated[int, Depends(_get_declared_status_code)]


async def _get_request_hash(
    request: Request,
    idempotency_hmac_secret: SecretStr,
) -> str:
    """Get hashed request, url-endpoint and http method.

    Args:
        request: default FastApi Request class.
        idempotency_hmac_secret: Service secret used to sign the normalized request.

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
    secret = idempotency_hmac_secret.get_secret_value().encode()

    return hmac.new(
        key=secret,
        msg=request_data,
        digestmod=hashlib.sha256,
    ).hexdigest()


def _get_idempotency_key(key: Annotated[UUID, Header(alias="Idempotency-Key")]) -> UUID:
    """Get Idempotency key from header.

    Args:
        key: wait Key from "Idempotency-Key" header.

    Returns:
        UUID: Idempotency key.
    """
    return key


IdempotencyKeyDependency = Annotated[UUID, Depends(_get_idempotency_key)]


def make_idempotency_service_dependency(
    repository_dependency: Callable[..., IdempotencyAbstractRepository],
    secret_dependency: Callable[..., SecretStr],
):
    """Build an idempotency dependency using the service's repository and secret."""

    async def get_request_hash(
        request: Request,
        secret: Annotated[SecretStr, Depends(secret_dependency)],
    ) -> str:
        return await _get_request_hash(
            request=request,
            idempotency_hmac_secret=secret,
        )

    def get_idempotency_service(
        idempotency_repository: Annotated[
            IdempotencyAbstractRepository,
            Depends(repository_dependency),
        ],
        idempotency_key: IdempotencyKeyDependency,
        status_code: DeclaredStatusCodeDependency,
        hashed_request: Annotated[str, Depends(get_request_hash)],
    ) -> IdempotencyAbstractService:
        return IdempotencyDBService(
            idempotency_repository=idempotency_repository,
            idempotency_key=idempotency_key,
            status_code=status_code,
            hashed_request=hashed_request,
        )

    return get_idempotency_service
