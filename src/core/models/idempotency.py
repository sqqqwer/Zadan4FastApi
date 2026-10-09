from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class Idempotency(BaseModel):
    """Database model for saved idempotent responses.

    Attributes:
        id: UUID
        scope: str
        key: UUID
        request_hash: str
        status_code: int
        response_body: dict[str, Any]
        created_at: datetime
    """

    __tablename__ = "idempotency"

    scope: Mapped[str]
    key: Mapped[UUID]
    request_hash: Mapped[str]
    status_code: Mapped[int]
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("scope", "key", name="unique_pair_scope_key"),)
