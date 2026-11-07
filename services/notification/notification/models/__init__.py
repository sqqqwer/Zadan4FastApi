from .base import NotificationBaseModelWithoutId
from .inbox_messages import InboxMessagesNotification

__all__ = ["InboxMessagesNotification", "NotificationBaseModelWithoutId"]

metadata = NotificationBaseModelWithoutId.metadata
