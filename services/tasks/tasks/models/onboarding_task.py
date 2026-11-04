from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TasksBaseModelWithoutId


class OnboardingTask(TasksBaseModelWithoutId):
    """Keep task ownership and a cancellation marker before or after task creation."""

    __tablename__ = "onboarding_task"

    saga_id: Mapped[UUID] = mapped_column(primary_key=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    task_id: Mapped[UUID | None]
    cancelled: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
