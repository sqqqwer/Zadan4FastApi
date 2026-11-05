from datetime import UTC, datetime
from functools import partial
from unittest.mock import MagicMock

from aiokafka.structs import ConsumerRecord
from sqlalchemy import select

from auth.events import subscribe_handlers as subscribe_auth
from auth.models.inbox_messages import InboxMessagesAuth
from auth.models.outbox_messages import OutboxMessagesAuth
from org.events import subscribe_handlers as subscribe_org
from org.models.inbox_messages import InboxMessagesOrg
from org.models.outbox_messages import OutboxMessagesOrg
from saga.events import subscribe_handlers as subscribe_saga
from saga.models.inbox_messages import InboxMessagesSaga
from saga.models.outbox_messages import OutboxMessagesSaga
from shared.events.bus import KafkaEventsBus
from shared.events.envelope import EventEnvelope
from shared.events.kafka_adapters import KafkaEventConsumer
from shared.events.types import EventType
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.uow.session_scope import session_scope
from tasks.events import subscribe_handlers as subscribe_tasks
from tasks.models.inbox_messages import InboxMessagesTasks
from tasks.models.outbox_messages import OutboxMessagesTasks

OUTBOX_MODELS = {
    "auth": OutboxMessagesAuth,
    "org": OutboxMessagesOrg,
    "tasks": OutboxMessagesTasks,
    "saga": OutboxMessagesSaga,
}
INBOX_MODELS = {
    "auth": InboxMessagesAuth,
    "org": InboxMessagesOrg,
    "tasks": InboxMessagesTasks,
    "saga": InboxMessagesSaga,
}
SUBSCRIPTIONS = {"auth": subscribe_auth, "org": subscribe_org, "tasks": subscribe_tasks, "saga": subscribe_saga}
COMMAND_TARGETS = {
    EventType.ORG_ASSIGN_EMPLOYEE: "org",
    EventType.ORG_UNASSIGN_EMPLOYEE: "org",
    EventType.TASKS_CREATE_WELCOME_TASK: "tasks",
    EventType.TASKS_CANCEL_WELCOME_TASK: "tasks",
    EventType.AUTH_INVALIDATE_INVITE: "auth",
}


class OnboardingSystem:
    """Replace delivery only; run real consumers, handlers, repositories and transactions."""

    def __init__(self, factories, correlation_id):
        """Share only serialized envelopes across each service's isolated database."""
        self.factories = factories
        self.correlation_id = correlation_id
        self.consumers = {}
        self.history: list[EventEnvelope] = []

    async def start(self):
        """Build the production subscriptions with a disconnected Kafka transport."""
        for service, factory in self.factories.items():
            producer = MagicMock()
            bus = KafkaEventsBus("unused:9092", producer=producer)
            await SUBSCRIPTIONS[service](bus)
            self.consumers[service] = KafkaEventConsumer(
                bus=bus,
                inbox_factory=partial(InboxSqlAlchemyRepository, model=INBOX_MODELS[service]),
                consumer_name=f"tests.{service}",
                kafka_bootstrap_servers="unused:9092",
                session_factory=factory,
            )

    async def deliver(self, service: str, envelope: EventEnvelope):
        """Deliver one envelope through the actual inbox transaction."""
        raw = envelope.model_dump_json().encode()
        message = ConsumerRecord(
            topic=f"{envelope.producer}.events",
            partition=0,
            offset=0,
            timestamp=0,
            timestamp_type=0,
            key=str(envelope.aggregate_id).encode(),
            value=raw,
            checksum=None,
            serialized_key_size=36,
            serialized_value_size=len(raw),
            headers=(),
        )
        await self.consumers[service]._process_message(message)

    async def drain(self):
        """Relay this test's outbox events until the finite saga has no pending messages."""
        for _ in range(20):
            delivered = False
            for service, model in OUTBOX_MODELS.items():
                async with session_scope(self.factories[service]) as session:
                    rows = (
                        await session.scalars(
                            select(model)
                            .where(
                                model.published_at.is_(None),
                                model.envelope["correlation_id"].astext == str(self.correlation_id),
                            )
                            .order_by(model.id)
                        )
                    ).all()
                    events = [EventEnvelope.model_validate(row.envelope) for row in rows]
                    for row in rows:
                        row.published_at = datetime.now(UTC)
                for event in events:
                    self.history.append(event)
                    if event.event_type == EventType.TASK_STATUS_CHANGED:
                        continue
                    target = COMMAND_TARGETS.get(event.event_type, "saga")
                    await self.deliver(target, event)
                    delivered = True
            if not delivered:
                return
        raise AssertionError("Onboarding did not finish within 20 delivery rounds")
