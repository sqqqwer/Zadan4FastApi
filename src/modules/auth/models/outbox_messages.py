from src.shared.outbox.model_mixin import OutboxMessagesMixin

from .base import AuthBaseModelWithoutId


class OutboxMessagesAuth(OutboxMessagesMixin, AuthBaseModelWithoutId):
    """Database model for outgoing events of the auth module.

    Attributes:
        id: int
        event_id: UUID
        event_type: str
        aggregate_id: UUID
        dedup_key: str
        payload: dict[str, Any]
        envelope: dict[str, Any]
        created_at: datetime
        published_at: datetime | None
        attempts: int
        last_error: str | None
    """
