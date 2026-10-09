import datetime
import logging
from abc import ABC, abstractmethod
from typing import Any, override
from uuid import UUID

from ..repositories.idempotency import IdempotencyAbstractRepository
from ..resources.exceptions import IdempotencyDifferentRequestError
from ..schemas.idempotency import IdempotencyCreateRepositoryScheme

logger = logging.getLogger(__name__)


class IdempotencyAbstractService(ABC):
    """Abstract idempotency service."""

    def __init__(
        self,
        idempotency_key: UUID,
        status_code: int,
        hashed_request: str,
    ):
        """Initialize the idempotency service.

        Args:
            idempotency_key: Idempotency key from the request headers.
            status_code: Status code declared by the endpoint.
            hashed_request: Hashed request.
        """
        self.idempotency_key = idempotency_key
        self.status_code = status_code
        self.hashed_request = hashed_request

    @abstractmethod
    async def check_operation(
        self,
        operation_name: str,
    ) -> dict[str, Any] | None:
        """Get an idempotency object by idempotency_key and operation_name.

        Returns:
            dict[str, Any]: Previously saved response from the idempotency object.
            None: If the idempotency object is not found.
        """
        ...

    @abstractmethod
    async def save_operation(self, response_json: dict[str, Any]) -> None:
        """Save the response to a new idempotency object."""
        ...


class IdempotencyDBService(IdempotencyAbstractService):
    """Idempotency service that works with a database."""

    def __init__(
        self,
        idempotency_repository: IdempotencyAbstractRepository,
        idempotency_key: UUID,
        status_code: int,
        hashed_request: str,
    ):
        """Initialize the idempotency service.

        Args:
            idempotency_repository: Repository for working with idempotency objects.

            idempotency_key: Idempotency key from the request headers.
            status_code: Status code declared by the endpoint.
            hashed_request: Hashed request.
        """
        super().__init__(
            idempotency_key=idempotency_key,
            status_code=status_code,
            hashed_request=hashed_request,
        )
        self.idempotency_repository = idempotency_repository

        self._operation_name: str | None = None
        self._can_save: bool = False

    @override
    async def check_operation(
        self,
        operation_name: str,
    ) -> dict[str, Any] | None:
        """Get an idempotency object by idempotency_key and operation_name.

        Returns:
            dict[str, Any]: Previously saved response from the idempotency object.
            None: If the idempotency object is not found.

        Raises:
            IdempotencyDifferentRequestError: If request_hash does not match the current hash.
        """
        self._operation_name = operation_name

        await self.idempotency_repository.lock_by_scope_key(scope=self._operation_name, key=self.idempotency_key)

        idempotency_record = await self.idempotency_repository.retrieve_by_scope_key(
            scope=self._operation_name, key=self.idempotency_key
        )

        if idempotency_record is not None:
            if idempotency_record.request_hash != self.hashed_request:
                raise IdempotencyDifferentRequestError()
            logger.info(
                f"Idempotent request replayed: operation={operation_name}",
            )
            return idempotency_record.response_body

        self._can_save = True
        return idempotency_record

    @override
    async def save_operation(self, response_json: dict[str, Any]) -> None:
        """Save the response to a new idempotency object.

        Raises:
            RuntimeError: If save_operation() is called before check_operation().
            RuntimeError: If an idempotency record already exists.
        """
        if self._operation_name is None:
            raise RuntimeError(
                "Call check_operation() before save_operation() to check for an existing idempotency record."
            )
        if self._can_save is False:
            raise RuntimeError("Idempotency record already exists.")

        create_scheme = IdempotencyCreateRepositoryScheme(
            scope=self._operation_name,
            key=self.idempotency_key,
            request_hash=self.hashed_request,
            status_code=self.status_code,
            response_body=response_json,
            created_at=datetime.datetime.now(datetime.UTC),
        )

        await self.idempotency_repository.create(scheme=create_scheme)
