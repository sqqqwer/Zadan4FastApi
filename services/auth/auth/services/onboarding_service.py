from shared.events.envelope import EventEnvelope
from shared.events.onboarding import OnboardingCommand, reply_to_saga
from shared.events.types import EventType
from shared.outbox.repository import OutboxAbstractRepository

from ..repositories.onboarding import OnboardingRepository


class OnboardingService:
    """Apply the auth compensation and confirm its durable result."""

    def __init__(self, repository: OnboardingRepository, outbox_repository: OutboxAbstractRepository) -> None:
        """Use repositories from the current message's transaction."""
        self.repository = repository
        self.outbox_repository = outbox_repository

    async def invalidate_invite(self, envelope: EventEnvelope) -> None:
        """Confirm invalidation even when it was already applied or the invite is gone."""
        command = OnboardingCommand.from_envelope(envelope)
        await self.repository.invalidate_invite(command)
        await reply_to_saga(self.outbox_repository, envelope, EventType.AUTH_INVITE_INVALIDATED)
