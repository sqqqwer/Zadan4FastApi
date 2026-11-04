from uuid import UUID


class SagaNotFound(ValueError):
    """An onboarding result refers to an unknown saga."""

    def __init__(self, saga_id: UUID) -> None:
        """Include the unknown saga ID in the error."""
        super().__init__(f"Onboarding saga not found: saga_id={saga_id}")


class InvalidSagaEvent(ValueError):
    """An event does not satisfy the onboarding message contract."""
