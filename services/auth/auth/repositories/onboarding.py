from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.onboarding import OnboardingCommand

from ..models.invite import Invite
from ..models.members import Members
from ..models.secrets import Secrets
from ..resources.enums import InvitePurposeEnum


class OnboardingRepository:
    """Invalidate employee invites in the same transaction as the consumer's inbox."""

    def __init__(self, session: AsyncSession) -> None:
        """Use the current message's session."""
        self.session = session

    async def invalidate_invite(self, command: OnboardingCommand) -> None:
        """Invalidate an owned employee invite; absence or prior invalidation is successful."""
        invite = await self.session.scalar(select(Invite).where(Invite.id == command.invite_id).with_for_update())
        if invite is None:
            return
        if invite.purpose != InvitePurposeEnum.EMPLOYEE_INVITATION:
            raise ValueError("Onboarding compensation cannot invalidate another invite purpose")
        owner = (
            await self.session.execute(
                select(Secrets.user_id, Members.company_id)
                .outerjoin(Members, Members.user_id == Secrets.user_id)
                .where(Secrets.account_id == invite.account_id)
            )
        ).first()
        if owner is not None and (
            owner.user_id != command.user_id
            or (owner.company_id is not None and owner.company_id != command.company_id)
        ):
            raise ValueError("Onboarding invite belongs to another user or company")
        if invite.invalidated_at is None:
            invite.invalidated_at = datetime.now(UTC)
