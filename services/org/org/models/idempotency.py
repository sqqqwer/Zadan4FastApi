from shared.idempotency.model_mixin import IdempotencyMixin

from .base import OrgBaseModelWithoutId


class IdempotencyOrg(IdempotencyMixin, OrgBaseModelWithoutId):
    """Saved idempotent responses in the org service's database."""
