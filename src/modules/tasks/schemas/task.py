from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.schemas.base import BaseModelCreateScheme, BaseModelResponseScheme, BaseModelUpdateScheme

from ..resources.constants import MAX_TASK_ESTIMATED_TIME_IN_MINUTES
from ..resources.enums import TaskStatusEnum


class TaskEditableFieldsScheme(BaseModel):
    """Editable task fields.

    Attributes:
        title: str
        description: str | None
        deadline: datetime
        estimated_minutes: int
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
    """

    title: str
    description: str | None
    deadline: datetime
    estimated_minutes: int = Field(ge=0, le=MAX_TASK_ESTIMATED_TIME_IN_MINUTES)

    responsible_id: UUID

    observer_ids: list[UUID]
    executor_ids: list[UUID]


class TaskStatusScheme(BaseModel):
    """Task status schema.

    Attributes:
        status: TaskStatusEnum
    """

    status: TaskStatusEnum


class TaskScheme(TaskEditableFieldsScheme, TaskStatusScheme):
    """Task data with an author and a status.

    Attributes:
        title: str
        description: str | None
        deadline: datetime
        estimated_minutes: int
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
        status: TaskStatusEnum
        author_id: UUID
    """

    author_id: UUID


class TaskCreatePayloadScheme(BaseModelCreateScheme, BaseModelUpdateScheme, TaskEditableFieldsScheme):
    """Request data for creating or updating a task.

    Attributes:
        title: str
        description: str | None
        deadline: datetime
        estimated_minutes: int
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
    """


class TaskCreateRepositoryScheme(BaseModelCreateScheme, TaskScheme):
    """Data for creating a task in the repository.

    Attributes:
        title: str
        description: str | None
        deadline: datetime
        estimated_minutes: int
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
        status: TaskStatusEnum
        author_id: UUID
    """


class TaskUpdateRepositoryScheme(BaseModelUpdateScheme, TaskEditableFieldsScheme):
    """Data for updating a task in the repository.

    Attributes:
        title: str
        description: str | None
        deadline: datetime
        estimated_minutes: int
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
    """


class TaskResponseScheme(BaseModelResponseScheme, TaskScheme):
    """Task response schema.

    Attributes:
        id: UUID
        title: str
        description: str | None
        deadline: datetime
        estimated_minutes: int
        responsible_id: UUID
        observer_ids: list[UUID]
        executor_ids: list[UUID]
        status: TaskStatusEnum
        author_id: UUID
    """
