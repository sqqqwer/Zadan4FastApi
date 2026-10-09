from abc import abstractmethod
from typing import override
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.idempotency import Idempotency

from ..schemas.idempotency import IdempotencyCreateRepositoryScheme
from .base import BaseRepository


class IdempotencyAbstractRepository(BaseRepository):
    """Abstract repository for idempotency objects."""

    @abstractmethod
    async def lock_by_scope_key(self, scope: str, key: UUID) -> None:
        """Lock the idempotency operation by scope and key.

        Args:
            scope: Idempotency operation scope.
            key: Idempotency key.
        """
        ...

    @abstractmethod
    async def retrieve_by_scope_key(self, scope: str, key: UUID) -> Idempotency | None:
        """Get an idempotency record by scope and key.

        Args:
            scope: Idempotency operation scope.
            key: Idempotency key.

        Returns:
            Idempotency: Idempotency record.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create(self, scheme: IdempotencyCreateRepositoryScheme) -> Idempotency:
        """Create the idempotency record.

        Args:
            scheme: Data for creating an idempotency record.

        Returns:
            Idempotency: Idempotency record.
        """
        ...


class IdempotencySqlAlchemyRepository(IdempotencyAbstractRepository):
    """SQLAlchemy repository for idempotency objects."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: Database session used by the repository.
        """
        self.session = session

    @override
    async def lock_by_scope_key(self, scope: str, key: UUID) -> None:
        lock_key = f"idempotency:{scope}:{key}"

        stmt = select(
            func.pg_advisory_xact_lock(
                func.hashtextextended(lock_key, 0),
            )
        )
        await self.session.execute(stmt)

    @override
    async def retrieve_by_scope_key(self, scope: str, key: UUID) -> Idempotency | None:
        stmt = select(Idempotency).where(Idempotency.scope == scope, Idempotency.key == key)
        struct = await self.session.execute(stmt)
        return struct.scalar_one_or_none()

    @override
    async def create(self, scheme: IdempotencyCreateRepositoryScheme) -> Idempotency:
        idempotency = Idempotency(**scheme.model_dump())
        self.session.add(idempotency)
        return idempotency
