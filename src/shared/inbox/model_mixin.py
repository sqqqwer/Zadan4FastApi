from uuid import UUID

from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class InboxMessagesMixin:
    """Mixin with fields for processed incoming events.

    Attributes:
        consumer_name: Stable name of the event consumer.
        event_id: UUID of the processed event.
    """

    consumer_name: Mapped[str] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(primary_key=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Get the inbox table name.

        Returns:
            str: Name of the inbox table.
        """
        return "inbox_messages"
