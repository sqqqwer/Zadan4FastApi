import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from src.core.repositories.crud import CrudAbstractRepository
from src.core.resources.exceptions import NotFoundError
from src.core.schemas.base import BaseModelCreateScheme, BaseModelResponseScheme, BaseModelUpdateScheme
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract

logger = logging.getLogger(__name__)


class CrudAbstractService[
    CreateScheme: BaseModelCreateScheme,
    UpdateScheme: BaseModelUpdateScheme,
    ResponseScheme: BaseModelResponseScheme,
](ABC):
    """Abstract service for CRUD operations."""

    def __init__(
        self,
        crud_repository: CrudAbstractRepository,
        response_scheme: type[ResponseScheme],
        uow: UowAbstract,
        current_user_id: UUID,
        company_id: UUID,
    ):
        """Initialize the service.

        Args:
            crud_repository: Repository for CRUD operations.
            response_scheme: Schema used to build the response.
            uow: Unit of work for database operations.
            current_user_id: Current user ID.
            company_id: Company ID.
        """
        self.crud_repository = crud_repository
        self.response_scheme = response_scheme
        self.uow = uow
        self.current_user_id = current_user_id
        self.company_id = company_id

    async def list(self, limit: int, offset: int) -> Sequence[ResponseScheme]:
        """Get a list of objects.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            Sequence[ResponseScheme]: List of object responses.
        """
        objects = await self.crud_repository.list_all(limit, offset)
        response = [self.response_scheme.model_validate(obj) for obj in objects]

        logger.info(f"{self._get_model_name()} retrieved list: number={len(response)} limit={limit} offset={offset}.")

        return response

    async def retrieve(self, id: UUID) -> ResponseScheme:
        """Get the object by ID.

        Args:
            id: Object ID.

        Returns:
            ResponseScheme: Object response data.

        Raises:
            NotFoundError: If the requested object is not found.
        """
        obj = await self.crud_repository.retrieve(id=id)

        if obj is None:
            raise self._not_found_exception()

        response = self.response_scheme.model_validate(obj)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} retrieved: id={response.id}.")

        return response

    async def create(self, payload: CreateScheme, idempotency: IdempotencyAbstractService) -> ResponseScheme:
        """Create the object.

        Args:
            payload: Object data used by the operation.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            ResponseScheme: Object response data.

        Raises:
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
        """
        idempotency_record = await idempotency.check_operation(
            f"{self._get_model_name()}.create:v1:{self.company_id}:{self.current_user_id}"
        )
        if idempotency_record is not None:
            return self.response_scheme.model_validate(idempotency_record)

        obj = await self.crud_repository.create(scheme=payload)
        await self.uow.flush()
        response = self.response_scheme.model_validate(obj)

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} created: id={response.id}.")

        return response

    async def update(self, id: UUID, payload: UpdateScheme) -> ResponseScheme:
        """Update the object.

        Args:
            id: Object ID.
            payload: Object data used by the operation.

        Returns:
            ResponseScheme: Object response data.

        Raises:
            NotFoundError: If the requested object is not found.
        """
        obj = await self.crud_repository.retrieve(id=id)

        if obj is None:
            raise self._not_found_exception()

        await self.crud_repository.update(obj=obj, scheme=payload)
        response = self.response_scheme.model_validate(obj)
        await self.uow.commit()

        logger.info(f"{self._get_model_name()} updated: id={response.id}.")

        return response

    async def delete(self, id: UUID) -> None:
        """Delete the object.

        Args:
            id: Object ID.

        Raises:
            NotFoundError: If the requested object is not found.
        """
        obj = await self.crud_repository.retrieve(id=id)

        if obj is None:
            raise self._not_found_exception()

        await self.crud_repository.delete(obj=obj)
        await self.uow.commit()

        logger.info(f"{self._get_model_name()} deleted: id={id}.")

    @abstractmethod
    def _get_model_name(self) -> str:
        return "base_model"

    @abstractmethod
    def _not_found_exception(self) -> NotFoundError:
        return NotFoundError()
