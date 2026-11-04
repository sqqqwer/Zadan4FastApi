from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.onboarding import OnboardingCommand

from ..models.onboarding_assignment import OnboardingAssignment
from ..models.position import Position
from ..models.struct_adm import StructAdm
from ..models.struct_adm_positions import StructAdmPositions
from ..models.users_positions import UsersPositions


class OnboardingRepository:
    """Store the org participant's results without committing the inbox transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Use the current message's session."""
        self.session = session

    async def get_or_create(self, command: OnboardingCommand) -> OnboardingAssignment:
        """Lock one durable assignment or cancellation record per saga."""
        context = command.model_dump(mode="json")
        await self.session.execute(
            insert(OnboardingAssignment)
            .values(saga_id=command.saga_id, context=context, cancelled=False)
            .on_conflict_do_nothing(index_elements=[OnboardingAssignment.saga_id])
        )
        record = await self.session.scalar(
            select(OnboardingAssignment).where(OnboardingAssignment.saga_id == command.saga_id).with_for_update()
        )
        if record is None:
            raise RuntimeError("Org onboarding record disappeared")
        if record.context != context:
            raise ValueError("Org onboarding command changed identifiers for an existing saga")
        return record

    async def assign(self, record: OnboardingAssignment, command: OnboardingCommand) -> str | None:
        """Create a new binding, or return a permanent business refusal."""
        position = await self.session.scalar(
            select(Position)
            .where(Position.id == command.position_id, Position.company_id == command.company_id)
            .with_for_update()
        )
        if position is None:
            return "position_not_found"
        struct = await self.session.scalar(
            select(StructAdm)
            .where(StructAdm.id == command.struct_id, StructAdm.company_id == command.company_id)
            .with_for_update()
        )
        if struct is None:
            return "struct_not_found"
        struct_position = await self.session.scalar(
            select(StructAdmPositions)
            .where(
                StructAdmPositions.position_id == command.position_id,
                StructAdmPositions.struct_adm_id == command.struct_id,
            )
            .with_for_update()
        )
        if struct_position is None:
            return "position_not_in_struct"
        occupied = await self.session.scalar(
            select(UsersPositions.id).where(UsersPositions.position_id == command.position_id).limit(1)
        )
        if occupied is not None:
            return "position_occupied"

        record.binding_id = uuid4()
        self.session.add(
            UsersPositions(id=record.binding_id, user_id=command.user_id, position_id=command.position_id)
        )
        return None

    async def unassign(self, record: OnboardingAssignment) -> None:
        """Remove only the binding created by this saga and retain its cancellation marker."""
        record.cancelled = True
        if record.binding_id is not None:
            await self.session.execute(delete(UsersPositions).where(UsersPositions.id == record.binding_id))
