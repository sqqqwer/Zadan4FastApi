from shared.idempotency.model_mixin import IdempotencyMixin

from .base import AuthBaseModelWithoutId


class IdempotencyAuth(IdempotencyMixin, AuthBaseModelWithoutId):
    """Saved idempotent responses in the auth service's database."""
