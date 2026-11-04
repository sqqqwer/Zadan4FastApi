from shared.inbox.model_mixin import InboxMessagesMixin

from .base import SagaBaseModelWithoutId


class InboxMessagesSaga(InboxMessagesMixin, SagaBaseModelWithoutId):
    """Processed events of the onboarding orchestrator."""
