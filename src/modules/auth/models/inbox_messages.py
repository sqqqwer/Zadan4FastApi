from src.shared.inbox.model_mixin import InboxMessagesMixin

from .base import AuthBaseModelWithoutId


class InboxMessagesAuth(InboxMessagesMixin, AuthBaseModelWithoutId):
    """Database model for processed incoming events of the auth module.

    Attributes:
        consumer_name: Stable name of the event consumer.
        event_id: UUID of the processed event.
    """
