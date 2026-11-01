from shared.idempotency.model_mixin import IdempotencyMixin

from .base import TasksBaseModelWithoutId


class IdempotencyTasks(IdempotencyMixin, TasksBaseModelWithoutId):
    """Saved idempotent responses in the tasks service's database."""
