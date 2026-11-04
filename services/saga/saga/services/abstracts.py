import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from shared.events.envelope import EventEnvelope
from shared.events.types import EventType
from shared.outbox.repository import OutboxAbstractRepository

from ..models.saga import Saga
from ..repositories.abstracts import SagaAbstractRepository
from ..resources.exceptions import InvalidSagaEvent, SagaNotFound
from ..schemas.saga import SagaResultPayload, StalledSagaResponse, StalledSagasResponse
from .constants import EVENT_PRODUCER

logger = logging.getLogger(__name__)


class SagaAbstractService(ABC):
    """Shared infrastructure for saga scenarios in the consumer's transaction."""

    def __init__(self, saga_repository: SagaAbstractRepository, outbox_repository: OutboxAbstractRepository) -> None:
        """Use repositories bound to the same session as the consumer's inbox."""
        self.saga_repository = saga_repository
        self.outbox_repository = outbox_repository

    @property
    @abstractmethod
    def saga_type(self) -> str:
        """Identify the scenario independently of its individual saga instances."""
        ...

    @abstractmethod
    async def start(self, envelope: EventEnvelope) -> None:
        """Validate a start event, persist initial state and enqueue the first command."""
        ...

    @abstractmethod
    async def handle(self, envelope: EventEnvelope) -> None:
        """Apply a participant's reply through the scenario's state and step guards."""
        ...

    async def list_stalled(self, timeout_seconds: float) -> StalledSagasResponse:
        """Get overdue steps of all scenarios using the same cutoff as the monitor."""
        now = datetime.now(UTC)
        sagas = await self.saga_repository.list_stalled(now - timedelta(seconds=timeout_seconds))
        items = [
            StalledSagaResponse(
                saga_id=saga.saga_id,
                saga_type=saga.saga_type,
                business_key=saga.business_key,
                state=saga.state,
                step=saga.step,
                updated_at=saga.updated_at,
                waiting_seconds=(now - saga.updated_at).total_seconds(),
                correlation_id=saga.context["correlation_id"],
            )
            for saga in sagas
        ]
        return StalledSagasResponse(timeout_seconds=timeout_seconds, total=len(items), items=items)

    async def log_stalled(self, timeout_seconds: float) -> None:
        """Report overdue steps without automatically cancelling them."""
        response = await self.list_stalled(timeout_seconds)
        for saga in response.items:
            logger.warning(
                "Saga step timeout: saga_id=%s saga_type=%s state=%s step=%s waiting_seconds=%.1f correlation_id=%s",
                saga.saga_id,
                saga.saga_type,
                saga.state,
                saga.step,
                saga.waiting_seconds,
                saga.correlation_id,
                extra={"correlation_id": str(saga.correlation_id)},
            )

    async def _load_saga(self, envelope: EventEnvelope) -> Saga:
        self._check_version(envelope)
        payload = SagaResultPayload.model_validate(envelope.payload)
        saga = await self.saga_repository.get_for_update(payload.saga_id)
        if saga is None:
            raise SagaNotFound(payload.saga_id)
        if saga.saga_type != self.saga_type:
            raise InvalidSagaEvent(f"Unexpected scenario for saga_id={saga.saga_id}: {saga.saga_type}")
        if str(envelope.correlation_id) != saga.context["correlation_id"]:
            raise InvalidSagaEvent(f"Correlation ID does not match saga_id={saga.saga_id}")
        return saga

    async def _send(self, saga: Saga, command: EventType, source: EventEnvelope) -> None:
        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=command,
            aggregate_id=saga.saga_id,
            occurred_at=datetime.now(UTC),
            correlation_id=UUID(saga.context["correlation_id"]),
            causation_id=source.event_id,
            producer=EVENT_PRODUCER,
            payload={**saga.context, "saga_id": str(saga.saga_id), "saga_type": saga.saga_type},
        )
        await self.outbox_repository.add(envelope, dedup_key=f"saga:{saga.saga_id}:{command.value}")

    @staticmethod
    def _check_version(envelope: EventEnvelope) -> None:
        if envelope.schema_version != 1:
            raise InvalidSagaEvent(f"Unsupported saga schema_version={envelope.schema_version}")

    @staticmethod
    def _log_transition(saga: Saga, envelope: EventEnvelope) -> None:
        logger.info(
            "Saga transition: saga_id=%s saga_type=%s state=%s step=%s event_type=%s event_id=%s correlation_id=%s",
            saga.saga_id,
            saga.saga_type,
            saga.state,
            saga.step,
            envelope.event_type,
            envelope.event_id,
            saga.context["correlation_id"],
            extra={"correlation_id": saga.context["correlation_id"]},
        )
