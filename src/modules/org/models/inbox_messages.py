from src.shared.inbox.model_mixin import InboxMessagesMixin

from .base import OrgBaseModelWithoutId


class InboxMessagesOrg(InboxMessagesMixin, OrgBaseModelWithoutId):
    """Database model for processed incoming events of the org module.

    Attributes:
        consumer_name: Stable name of the event consumer.
        event_id: UUID of the processed event.
    """
