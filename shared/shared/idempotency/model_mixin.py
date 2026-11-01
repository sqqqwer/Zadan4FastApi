from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class IdempotencyMixin:
    """Mixin with fields for saved idempotent responses.

    Attributes:
        id: UUID
        scope: str
        key: UUID
        request_hash: str
        status_code: int
        response_body: dict[str, Any]
        created_at: datetime
    """

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scope: Mapped[str]
    key: Mapped[UUID]
    request_hash: Mapped[str]
    status_code: Mapped[int]
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Get the idempotency table name."""
        return "idempotency"

    @declared_attr.directive
    def __table_args__(cls) -> tuple[UniqueConstraint]:
        """Create a separate uniqueness constraint for each service table."""
        return (UniqueConstraint("scope", "key", name="unique_pair_scope_key"),)
