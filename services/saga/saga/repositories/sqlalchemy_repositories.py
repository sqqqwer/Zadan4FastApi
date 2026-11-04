from datetime import UTC, datetime
from typing import override
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.saga import Saga
from ..resources.enums import SagaState
from ..schemas.saga import SagaCreateScheme
from .abstracts import SagaAbstractRepository


class SagaSqlAlchemyRepository(SagaAbstractRepository):
    """PostgreSQL storage shared by scenarios, with deduplicated starts and row locks."""

    def __init__(self, session: AsyncSession) -> None:
        """Use the session shared with the orchestrator's inbox and outbox."""
        self.session = session

    @override
    async def create_once(self, scheme: SagaCreateScheme) -> Saga | None:
        statement = (
            insert(Saga)
            .values(
                saga_id=uuid4(),
                saga_type=scheme.saga_type,
                business_key=scheme.business_key,
                state=SagaState.RUNNING,
                step=scheme.step,
                context=scheme.context,
                updated_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=[Saga.saga_type, Saga.business_key])
            .returning(Saga)
        )
        return await self.session.scalar(statement)

    @override
    async def get_for_update(self, saga_id: UUID) -> Saga | None:
        statement = (
            select(Saga).where(Saga.saga_id == saga_id).with_for_update().execution_options(populate_existing=True)
        )
        return await self.session.scalar(statement)

    @override
    async def list_stalled(self, before: datetime) -> list[Saga]:
        statement = (
            select(Saga)
            .where(
                Saga.state.in_((SagaState.RUNNING, SagaState.COMPENSATING)),
                Saga.updated_at < before,
            )
            .order_by(Saga.updated_at, Saga.saga_id)
        )
        return list((await self.session.scalars(statement)).all())
