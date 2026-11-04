from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from ..models.saga import Saga
from ..schemas.saga import SagaCreateScheme


class SagaAbstractRepository(ABC):
    """Storage of scenario state in the consumer's transaction."""

    @abstractmethod
    async def create_once(self, scheme: SagaCreateScheme) -> Saga | None:
        """Insert a saga, or return None if this scenario and business key already exist."""
        ...

    @abstractmethod
    async def get_for_update(self, saga_id: UUID) -> Saga | None:
        """Lock the saga until the surrounding transaction finishes."""
        ...

    @abstractmethod
    async def list_stalled(self, before: datetime) -> list[Saga]:
        """Find unfinished sagas whose current step exceeded its deadline."""
        ...
