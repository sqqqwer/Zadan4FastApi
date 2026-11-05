from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from auth.models.invite import Invite
from org.models.onboarding_assignment import OnboardingAssignment
from org.models.position import Position
from org.models.users_positions import UsersPositions
from saga.api.v1 import saga as saga_routes
from saga.main import app
from saga.models.saga import Saga
from saga.resources.enums import OnboardingStep, SagaState
from shared.events.types import EventType
from shared.uow.session_scope import session_scope
from tasks.models.onboarding_task import OnboardingTask
from tasks.models.task import Task
from tasks.resources.enums import TaskStatusEnum


async def test_successful_onboarding(onboarding_system, registered_event):
    """The real participants bind the employee and create one welcome task before completion."""
    system = onboarding_system

    await system.deliver("saga", registered_event)
    await system.drain()
    await system.deliver("saga", registered_event)
    await system.deliver("saga", registered_event.model_copy(update={"event_id": uuid4()}))
    await system.drain()

    async with system.factories["saga"]() as session:
        sagas = (
            await session.scalars(select(Saga).where(Saga.business_key == registered_event.payload["invite_id"]))
        ).all()
        assert len(sagas) == 1
        saga = sagas[0]
        assert saga.state == SagaState.COMPLETED and saga.step == OnboardingStep.DONE
    async with system.factories["org"]() as session:
        assignment = await session.get(OnboardingAssignment, saga.saga_id)
        assert assignment.cancelled is False
        binding = await session.get(UsersPositions, assignment.binding_id)
        assert binding.user_id == UUID(registered_event.payload["user_id"])
        assert binding.position_id == UUID(registered_event.payload["position_id"])
    async with system.factories["tasks"]() as session:
        record = await session.get(OnboardingTask, saga.saga_id)
        task = await session.get(Task, record.task_id)
        assert task.responsible_id == UUID(registered_event.payload["user_id"])
        assert task.status == TaskStatusEnum.CREATED
        assert (
            await session.scalar(
                select(func.count()).select_from(Task).where(Task.responsible_id == task.responsible_id)
            )
            == 1
        )
    assert [event.event_type for event in system.history] == [
        EventType.ORG_ASSIGN_EMPLOYEE,
        EventType.ORG_EMPLOYEE_ASSIGNED,
        EventType.TASKS_CREATE_WELCOME_TASK,
        EventType.TASKS_WELCOME_TASK_CREATED,
    ]


@pytest.mark.parametrize("failure", ["deleted_position", "occupied_position"])
async def test_failed_org_step_is_compensated(onboarding_system, registered_event, failure):
    """A business refusal finishes all compensations and leaves the other employee's binding intact."""
    system = onboarding_system
    payload = registered_event.payload
    occupied_binding = uuid4()
    async with session_scope(system.factories["org"]) as session:
        if failure == "deleted_position":
            await session.execute(delete(Position).where(Position.id == UUID(payload["position_id"])))
        else:
            session.add(UsersPositions(id=occupied_binding, user_id=uuid4(), position_id=payload["position_id"]))

    await system.deliver("saga", registered_event)
    await system.drain()

    async with system.factories["saga"]() as session:
        saga = await session.scalar(select(Saga).where(Saga.business_key == payload["invite_id"]))
        assert saga.state == SagaState.COMPENSATED and saga.step == OnboardingStep.DONE
        assert saga.context["failure_reason"] == (
            "position_not_found" if failure == "deleted_position" else "position_occupied"
        )
    async with system.factories["org"]() as session:
        assignment = await session.get(OnboardingAssignment, saga.saga_id)
        assert assignment.cancelled is True
        assert assignment.binding_id is None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(UsersPositions)
                .where(UsersPositions.user_id == UUID(payload["user_id"]))
            )
            == 0
        )
        if failure == "occupied_position":
            assert await session.get(UsersPositions, occupied_binding) is not None
    async with system.factories["tasks"]() as session:
        record = await session.get(OnboardingTask, saga.saga_id)
        assert record.cancelled is True and record.task_id is None
        assert (
            await session.scalar(
                select(func.count()).select_from(Task).where(Task.responsible_id == UUID(payload["user_id"]))
            )
            == 0
        )
    async with system.factories["auth"]() as session:
        invite = await session.get(Invite, UUID(payload["invite_id"]))
        assert invite.invalidated_at is not None
    assert [event.event_type for event in system.history] == [
        EventType.ORG_ASSIGN_EMPLOYEE,
        EventType.ORG_EMPLOYEE_ASSIGNMENT_FAILED,
        EventType.TASKS_CANCEL_WELCOME_TASK,
        EventType.TASKS_WELCOME_TASK_CANCELLED,
        EventType.ORG_UNASSIGN_EMPLOYEE,
        EventType.ORG_EMPLOYEE_UNASSIGNED,
        EventType.AUTH_INVALIDATE_INVITE,
        EventType.AUTH_INVITE_INVALIDATED,
    ]
    assert all(event.correlation_id == registered_event.correlation_id for event in system.history)


async def test_guard_ignores_repeated_and_late_replies(onboarding_system, registered_event):
    """A repeated success with a fresh delivery ID cannot send the next command twice."""
    system = onboarding_system
    await system.deliver("saga", registered_event)
    await system.drain()
    reply = next(event for event in system.history if event.event_type == EventType.ORG_EMPLOYEE_ASSIGNED)
    before = list(system.history)

    await system.deliver("saga", reply)
    await system.deliver("saga", reply.model_copy(update={"event_id": uuid4()}))
    await system.drain()

    async with system.factories["saga"]() as session:
        saga = await session.get(Saga, reply.aggregate_id)
        assert saga.state == SagaState.COMPLETED and saga.step == OnboardingStep.DONE
    assert system.history == before


async def test_repeated_compensations_are_idempotent(onboarding_system, registered_event):
    """Fresh-ID repeated compensation commands cancel existing effects exactly once."""
    system = onboarding_system
    await system.deliver("saga", registered_event)
    await system.drain()
    assignment_command = next(event for event in system.history if event.event_type == EventType.ORG_ASSIGN_EMPLOYEE)
    saga_id = assignment_command.aggregate_id
    commands = (
        ("tasks", EventType.TASKS_CANCEL_WELCOME_TASK),
        ("org", EventType.ORG_UNASSIGN_EMPLOYEE),
        ("auth", EventType.AUTH_INVALIDATE_INVITE),
    )
    for service, event_type in commands:
        command = assignment_command.model_copy(update={"event_id": uuid4(), "event_type": event_type})
        await system.deliver(service, command)
        await system.deliver(service, command.model_copy(update={"event_id": uuid4()}))
    async with system.factories["tasks"]() as session:
        record = await session.get(OnboardingTask, saga_id)
        task = await session.get(Task, record.task_id)
        assert record.cancelled is True
        assert task.status == TaskStatusEnum.CANCELED
        assert task.status_version == 1
    async with system.factories["org"]() as session:
        record = await session.get(OnboardingAssignment, saga_id)
        assert record.cancelled is True
        assert await session.get(UsersPositions, record.binding_id) is None
    async with system.factories["auth"]() as session:
        invite = await session.get(Invite, UUID(registered_event.payload["invite_id"]))
        assert invite.invalidated_at is not None


async def test_stalled_endpoint_lists_only_overdue_unfinished_sagas(service_factories, registered_event, monkeypatch):
    """The monitoring endpoint excludes recent steps and completed or compensated sagas."""
    expected_timeout = 60
    settings = saga_routes.get_settings().model_copy(update={"saga_step_timeout_seconds": expected_timeout})
    monkeypatch.setattr(saga_routes, "get_settings", lambda: settings)
    now = datetime.now(UTC)
    overdue_ids = []
    async with session_scope(service_factories["saga"]) as session:
        for state, old in (
            (SagaState.RUNNING, True),
            (SagaState.COMPENSATING, True),
            (SagaState.RUNNING, False),
            (SagaState.COMPLETED, True),
            (SagaState.COMPENSATED, True),
        ):
            saga_id = uuid4()
            if old and state in (SagaState.RUNNING, SagaState.COMPENSATING):
                overdue_ids.append(str(saga_id))
            session.add(
                Saga(
                    saga_id=saga_id,
                    saga_type="employee_onboarding",
                    business_key=str(uuid4()),
                    state=state,
                    step=OnboardingStep.ORG_ASSIGN,
                    context={"correlation_id": str(registered_event.correlation_id)},
                    updated_at=now - timedelta(days=1) if old else now,
                )
            )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/saga/api/v1/stalled")

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["timeout_seconds"] == expected_timeout
    assert {item["saga_id"] for item in data["items"]} == set(overdue_ids)
    assert data["total"] == len(overdue_ids)
    assert all(item["waiting_seconds"] > data["timeout_seconds"] for item in data["items"])
    assert all(item["correlation_id"] == str(registered_event.correlation_id) for item in data["items"])
