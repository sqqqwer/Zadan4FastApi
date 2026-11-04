from enum import StrEnum


class SagaState(StrEnum):
    """Lifecycle states shared by saga scenarios."""

    RUNNING = "RUNNING"
    COMPENSATING = "COMPENSATING"
    COMPLETED = "COMPLETED"
    COMPENSATED = "COMPENSATED"


class OnboardingStep(StrEnum):
    """Pending commands of the employee onboarding scenario."""

    ORG_ASSIGN = "ORG_ASSIGN"
    TASK_CREATE = "TASK_CREATE"
    TASK_CANCEL = "TASK_CANCEL"
    ORG_UNASSIGN = "ORG_UNASSIGN"
    INVITE_INVALIDATE = "INVITE_INVALIDATE"
    DONE = "DONE"
