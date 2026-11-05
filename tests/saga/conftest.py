import os
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import saga.dependencies.session as saga_sessions
from auth.models.invite import Invite
from auth.resources.enums import InvitePurposeEnum
from org.models.position import Position
from org.models.struct_adm import StructAdm
from org.models.struct_adm_positions import StructAdmPositions
from shared.events import kafka_adapters
from shared.events.envelope import EventEnvelope
from shared.events.types import EventType
from shared.uow.session_scope import session_scope
from tests.events.stubs import StubKafkaReader

from .stubs import OnboardingSystem


@pytest.fixture
def registered_event() -> EventEnvelope:
    """Build the onboarding context using identifiers unique to this test."""
    payload = {field: str(uuid4()) for field in ("user_id", "company_id", "invite_id", "position_id", "struct_id")}
    return EventEnvelope(
        event_id=uuid4(),
        event_type=EventType.EMPLOYEE_REGISTERED,
        aggregate_id=UUID(payload["user_id"]),
        occurred_at=datetime.now(UTC),
        correlation_id=uuid4(),
        producer="auth",
        payload=payload,
    )


@pytest.fixture
async def service_factories(monkeypatch):
    """Roll back each service's outer transaction after all per-message savepoints close."""
    async with AsyncExitStack() as stack:
        factories = {}
        for service, port in {"auth": 5433, "org": 5434, "tasks": 5435, "saga": 5436}.items():
            url = os.environ.get(
                f"{service.upper()}_DATABASE_URL", f"postgresql+asyncpg://test:test@localhost:{port}/test"
            )
            engine = create_async_engine(url)
            stack.push_async_callback(engine.dispose)
            connection = await stack.enter_async_context(engine.connect())
            transaction = await connection.begin()
            stack.push_async_callback(transaction.rollback)
            factories[service] = async_sessionmaker(
                connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
        monkeypatch.setattr(saga_sessions, "async_session_factory", factories["saga"])
        yield factories


@pytest.fixture
async def onboarding_system(service_factories, registered_event, monkeypatch):
    """Seed valid org targets and the employee invite, leaving transport under test control."""
    monkeypatch.setattr(kafka_adapters, "AIOKafkaConsumer", lambda *args, **kwargs: StubKafkaReader())
    payload = registered_event.payload
    async with session_scope(service_factories["org"]) as session:
        position = Position(id=payload["position_id"], company_id=payload["company_id"], name="Test position")
        struct = StructAdm(
            id=payload["struct_id"], company_id=payload["company_id"], name="Test struct", path=f"test_{uuid4().hex}"
        )
        session.add(StructAdmPositions(position=position, struct_adm=struct))
    async with session_scope(service_factories["auth"]) as session:
        session.add(
            Invite(
                id=payload["invite_id"],
                token_hash=uuid4().hex,
                recipient_email="onboarding@example.com",
                purpose=InvitePurposeEnum.EMPLOYEE_INVITATION,
                used_at=datetime.now(UTC),
                expired_at=datetime.now(UTC) + timedelta(hours=1),
                position_id=payload["position_id"],
                struct_id=payload["struct_id"],
            )
        )
    system = OnboardingSystem(service_factories, registered_event.correlation_id)
    await system.start()
    return system
