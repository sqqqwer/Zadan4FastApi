from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..resources.enums import SagaState
from .base import SagaBaseModelWithoutId


class Saga(SagaBaseModelWithoutId):
    """Persisted progress, deduplicated by scenario and its business key."""

    __tablename__ = "saga"

    saga_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    saga_type: Mapped[str] = mapped_column(Text)
    business_key: Mapped[str] = mapped_column(Text)
    state: Mapped[SagaState] = mapped_column(SAEnum(SagaState, name="saga_state", schema="saga"))
    step: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("saga_type", "business_key", name="uq_saga_type_business_key"),
        Index("ix_saga_state_updated_at", "state", "updated_at"),
    )
