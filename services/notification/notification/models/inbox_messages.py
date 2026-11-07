from shared.inbox.model_mixin import InboxMessagesMixin

from .base import NotificationBaseModelWithoutId


class InboxMessagesNotification(InboxMessagesMixin, NotificationBaseModelWithoutId):
    """Processed events of the notification consumer."""
