from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, CheckConstraint, DateTime, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from ..resources.constants import MAX_TASK_ESTIMATED_TIME_IN_MINUTES
from ..resources.enums import TaskStatusEnum
from .base import TasksBaseModel


class Task(TasksBaseModel):
    """Database model for a task.

    Attributes:
        id: UUID
        company_id: UUID
        title: str
        description: str | None
        deadline: datetime
        status: TaskStatusEnum
        estimated_minutes: int
        author_id: UUID
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
    """

    __tablename__ = "task"

    company_id: Mapped[UUID]

    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    status: Mapped[TaskStatusEnum] = mapped_column(
        SAEnum(
            TaskStatusEnum,
            name="task_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        )
    )
    estimated_minutes: Mapped[int] = mapped_column(
        default=0,
    )

    author_id: Mapped[UUID]
    responsible_id: Mapped[UUID]

    observer_ids: Mapped[list[UUID]] = mapped_column(ARRAY(Uuid()))
    executor_ids: Mapped[list[UUID]] = mapped_column(ARRAY(Uuid()))

    __table_args__ = (
        CheckConstraint("estimated_minutes >= 0", name="check_estimated_minutes_ge_zero"),
        CheckConstraint(
            f"estimated_minutes <= {MAX_TASK_ESTIMATED_TIME_IN_MINUTES}",
            name="check_estimated_minutes_le_max_value",
        ),
    )
