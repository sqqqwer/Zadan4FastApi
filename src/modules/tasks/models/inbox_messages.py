from src.shared.inbox.model_mixin import InboxMessagesMixin

from .base import TasksBaseModelWithoutId


class InboxMessagesTasks(InboxMessagesMixin, TasksBaseModelWithoutId):
    """Database model for processed incoming events of the tasks module.

    Attributes:
        consumer_name: Stable name of the event consumer.
        event_id: UUID of the processed event.
    """
