import logging
from datetime import UTC, datetime
from typing import override

from shared.events.envelope import EventEnvelope
from shared.events.types import EventType

from ..resources.enums import OnboardingStep, SagaState
from ..resources.exceptions import InvalidSagaEvent
from ..schemas.saga import EmployeeRegisteredPayload, SagaCreateScheme, SagaFailurePayload
from .abstracts import SagaAbstractService
from .constants import FAILURE_EVENTS

logger = logging.getLogger(__name__)


class OnboardingSagaService(SagaAbstractService):
    """Coordinate employee onboarding without committing the consumer's transaction."""

    saga_type = "employee_onboarding"

    @override
    async def start(self, envelope: EventEnvelope) -> None:
        """Start one onboarding per invite and enqueue the org assignment."""
        if envelope.event_type != EventType.EMPLOYEE_REGISTERED or envelope.producer != "auth":
            raise InvalidSagaEvent("Onboarding must start with employee.registered from auth")

        self._check_version(envelope)

        payload = EmployeeRegisteredPayload.model_validate(envelope.payload)
        if envelope.aggregate_id != payload.user_id:
            raise InvalidSagaEvent("employee.registered aggregate_id must equal user_id")

        saga = await self.saga_repository.create_once(
            SagaCreateScheme(
                saga_type=self.saga_type,
                business_key=str(payload.invite_id),
                step=OnboardingStep.ORG_ASSIGN,
                context={
                    **payload.model_dump(mode="json"),
                    "correlation_id": str(envelope.correlation_id),
                },
            )
        )
        if saga is None:
            logger.info("Onboarding already started: invite_id=%s", payload.invite_id)
            return

        await self._send(saga, EventType.ORG_ASSIGN_EMPLOYEE, envelope)
        self._log_transition(saga, envelope)

    @override
    async def handle(self, envelope: EventEnvelope) -> None:
        """Apply a reply only when its state, step and participant match the guard."""
        participant = envelope.event_type.value.split(".", maxsplit=1)[0]
        if envelope.producer != participant:
            raise InvalidSagaEvent(f"Unexpected producer for {envelope.event_type}: {envelope.producer}")

        if envelope.event_type in FAILURE_EVENTS:
            SagaFailurePayload.model_validate(envelope.payload)
        saga = await self._load_saga(envelope)

        command: EventType | None = None

        match (saga.state, saga.step, envelope.event_type):
            case (SagaState.RUNNING, OnboardingStep.ORG_ASSIGN, EventType.ORG_EMPLOYEE_ASSIGNED):
                saga.step = OnboardingStep.TASK_CREATE
                command = EventType.TASKS_CREATE_WELCOME_TASK

            case (SagaState.RUNNING, OnboardingStep.TASK_CREATE, EventType.TASKS_WELCOME_TASK_CREATED):
                saga.state = SagaState.COMPLETED
                saga.step = OnboardingStep.DONE

            case (SagaState.RUNNING, OnboardingStep.ORG_ASSIGN, EventType.ORG_EMPLOYEE_ASSIGNMENT_FAILED) | (
                SagaState.RUNNING,
                OnboardingStep.TASK_CREATE,
                EventType.TASKS_WELCOME_TASK_CREATION_FAILED,
            ):
                failure = SagaFailurePayload.model_validate(envelope.payload)
                saga.context = {**saga.context, "failure_reason": failure.reason, "failed_step": saga.step}
                saga.state = SagaState.COMPENSATING
                saga.step = OnboardingStep.TASK_CANCEL
                command = EventType.TASKS_CANCEL_WELCOME_TASK

            case (SagaState.COMPENSATING, OnboardingStep.TASK_CANCEL, EventType.TASKS_WELCOME_TASK_CANCELLED):
                saga.step = OnboardingStep.ORG_UNASSIGN
                command = EventType.ORG_UNASSIGN_EMPLOYEE

            case (SagaState.COMPENSATING, OnboardingStep.ORG_UNASSIGN, EventType.ORG_EMPLOYEE_UNASSIGNED):
                saga.step = OnboardingStep.INVITE_INVALIDATE
                command = EventType.AUTH_INVALIDATE_INVITE

            case (SagaState.COMPENSATING, OnboardingStep.INVITE_INVALIDATE, EventType.AUTH_INVITE_INVALIDATED):
                saga.state = SagaState.COMPENSATED
                saga.step = OnboardingStep.DONE

            case _:
                logger.info(
                    "Saga guard rejected event: saga_id=%s state=%s step=%s event_type=%s event_id=%s",
                    saga.saga_id,
                    saga.state,
                    saga.step,
                    envelope.event_type,
                    envelope.event_id,
                )
                return

        saga.updated_at = datetime.now(UTC)
        if command is not None:
            await self._send(saga, command, envelope)
        self._log_transition(saga, envelope)
