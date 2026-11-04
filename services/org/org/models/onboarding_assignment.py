from typing import Any
from uuid import UUID

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import OrgBaseModelWithoutId


class OnboardingAssignment(OrgBaseModelWithoutId):
    """Keep assignment ownership and cancellation even after a binding is deleted."""

    __tablename__ = "onboarding_assignment"

    saga_id: Mapped[UUID] = mapped_column(primary_key=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    binding_id: Mapped[UUID | None]
    cancelled: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    failure_reason: Mapped[str | None] = mapped_column(Text)
