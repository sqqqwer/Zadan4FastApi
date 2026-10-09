from abc import abstractmethod
from uuid import UUID

from src.core.models.base import BaseModel
from src.core.schemas.base import BaseModelCreateScheme, BaseModelUpdateScheme

from .base import BaseRepository


class CrudAbstractRepository[
    Model: BaseModel,
    CreateScheme: BaseModelCreateScheme,
    UpdateScheme: BaseModelUpdateScheme,
](BaseRepository):
    """Abstract repository for CRUD operations."""

    @abstractmethod
    async def list_all(self, limit: int, offset: int) -> list[Model]:
        """Get a list of objects.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            list[Model]: List of database objects.
        """
        ...

    @abstractmethod
    async def retrieve(self, id: UUID) -> Model | None:
        """Get the object by ID.

        Args:
            id: Object ID.

        Returns:
            Model: Database object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create(self, scheme: CreateScheme) -> Model:
        """Create the object.

        Args:
            scheme: Object data used by the operation.

        Returns:
            Model: Database object.
        """
        ...

    @abstractmethod
    async def update(self, obj: Model, scheme: UpdateScheme) -> Model:
        """Update the object.

        Args:
            obj: Database object to change.
            scheme: Object data used by the operation.

        Returns:
            Model: Database object.
        """
        ...

    @abstractmethod
    async def delete(self, obj: Model) -> None:
        """Delete the object.

        Args:
            obj: Database object to change.
        """
        ...
