from shared.outbox.model_mixin import OutboxMessagesMixin

from .base import SagaBaseModelWithoutId


class OutboxMessagesSaga(OutboxMessagesMixin, SagaBaseModelWithoutId):
    """Commands awaiting publication to saga.events."""
