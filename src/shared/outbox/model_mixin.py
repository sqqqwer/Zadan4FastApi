from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class OutboxMessagesMixin:
    """Mixin with fields for outgoing events.

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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[UUID] = mapped_column(unique=True)
    event_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[UUID]
    dedup_key: Mapped[str] = mapped_column(Text, unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Get the outbox table name.

        Returns:
            str: Name of the outbox table.
        """
        return "outbox_messages"

    @declared_attr.directive
    def __table_args__(cls) -> tuple[Index]:
        """Create an unpublished messages index for each outbox table.

        Returns:
            tuple[Index]: Index for messages awaiting publication.
        """
        return (
            Index(
                "ix_outbox_messages_unpublished_created_at",
                "created_at",
                postgresql_where=text("published_at IS NULL"),
            ),
        )
