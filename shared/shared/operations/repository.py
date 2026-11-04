from collections.abc import Sequence
from typing import Any, override

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.outbox.model_mixin import OutboxMessagesMixin

from .abstracts import OperationsAbstractRepository


class OperationsSqlAlchemyRepository(OperationsAbstractRepository):
    """Database checks and pending outbox queries for one service."""

    def __init__(self, session: AsyncSession, model: type[OutboxMessagesMixin]):
        """Use the session provided by the service's dependency."""
        self.session = session
        self.model = model

    @override
    async def check_connection(self) -> None:
        """Execute a lightweight query against the service's database."""
        await self.session.execute(text("SELECT 1"))

    @override
    async def rollback(self) -> None:
        """Roll back the session after a failed database check."""
        await self.session.rollback()

    @override
    async def count_pending_outbox(self) -> int:
        """Count all messages awaiting publication."""
        statement = select(func.count()).select_from(self.model).where(self.model.published_at.is_(None))
        return await self.session.scalar(statement) or 0

    @override
    async def list_pending_outbox(self, limit: int, offset: int) -> Sequence[dict[str, Any]]:
        """Get publication diagnostics, starting with the oldest messages."""
        statement = (
            select(
                self.model.id,
                self.model.event_id,
                self.model.event_type,
                self.model.envelope["correlation_id"].astext.label("correlation_id"),
                self.model.created_at,
                self.model.attempts,
                self.model.last_error,
            )
            .where(self.model.published_at.is_(None))
            .order_by(self.model.created_at, self.model.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return [dict(row) for row in result.mappings()]
