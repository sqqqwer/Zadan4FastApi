from src.core.resources.exceptions import (
    AppError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
)


class TasksModuleError(AppError):
    """Base error for the tasks module."""

    _message: str = "Tasks Module Error."


class TaskNotFound(TasksModuleError, NotFoundError):
    """The task is not found."""

    _message: str = "Task not found."


class TaskNewStatusMatchesCurrentStatus(TasksModuleError, ConflictError):
    """The task already has the requested status."""

    _message: str = "The task already has the requested status."


class InvalidTaskStatusTransition(TasksModuleError, ConflictError):
    """The requested task status transition is not allowed."""

    _message: str = "The requested status transition is not allowed."


class UserNotFound(TasksModuleError, NotFoundError):
    """The user is not found."""

    _message: str = "User not found."


class UserFromDifferentCompany(TasksModuleError, DomainValidationError):
    """The user belongs to a different company."""

    _message: str = "The user belongs to a different company."
