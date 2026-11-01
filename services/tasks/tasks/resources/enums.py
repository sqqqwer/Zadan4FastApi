from enum import StrEnum


class TaskStatusEnum(StrEnum):
    """Supported task statuses."""

    CREATED = "created"
    ACTIVE = "active"
    CANCELED = "canceled"
    IN_PROGRESS = "in_progress"
    NEED_REVIEW = "need_review"
    COMPLETED = "completed"
