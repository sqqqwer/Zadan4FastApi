import asyncio
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.main import app
from src.core.models.idempotency import Idempotency
from src.core.repositories.idempotency import IdempotencySqlAlchemyRepository
from src.core.resources.exceptions import IdempotencyDifferentRequestError
from src.core.schemas.token_claims import AccessTokenClaims
from src.modules.tasks.models.task import Task
from src.modules.tasks.schemas import TaskCreatePayloadScheme, TaskResponseScheme

from .constants import ENDPOINT, REQUEST_COUNT, TIMEOUT_SECONDS


async def wait_for_both_requests(session: AsyncSession, blocker_pid: int) -> None:
    """Wait until both requests are blocked by PostgreSQL advisory locks.

    Args:
        session: Database session holding the locks.
        blocker_pid: PostgreSQL process ID blocking both requests.
    """
    waiting_requests = text(
        """
        SELECT count(DISTINCT pid)
        FROM pg_locks
        WHERE locktype = 'advisory'
          AND NOT granted
          AND :blocker_pid = ANY(pg_blocking_pids(pid))
        """
    )
    while await session.scalar(waiting_requests, {"blocker_pid": blocker_pid}) != REQUEST_COUNT:
        await asyncio.sleep(0.01)


@pytest.mark.usefixtures("stub_tasks_user_directory", "fail_first_save")
@pytest.mark.parametrize(
    argnames=["scenario", "expected_status_codes", "expected_count"],
    argvalues=[
        ("same_request", [status.HTTP_201_CREATED, status.HTTP_201_CREATED], 1),
        ("different_body", [status.HTTP_201_CREATED, status.HTTP_409_CONFLICT], 1),
        ("different_keys", [status.HTTP_201_CREATED, status.HTTP_201_CREATED], 2),
        ("first_request_fails", [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR], 1),
    ],
)
async def test_concurrent_task_creation(  # noqa: PLR0913, PLR0917
    concurrent_db: async_sessionmaker[AsyncSession],
    operation_scope: str,
    stub_claims: AccessTokenClaims,
    task_create_payload: TaskCreatePayloadScheme,
    scenario: str,
    expected_status_codes: list[int],
    expected_count: int,
):
    """Check task creation idempotency for concurrent requests.

    Args:
        concurrent_db: Factory for independent test database sessions.
        operation_scope: Idempotency operation scope for the test admin.
        stub_claims: Access token claims of the test admin.
        task_create_payload: Task creation data.
        scenario: Concurrent request scenario.
        expected_status_codes: Expected HTTP status codes in ascending order.
        expected_count: Expected number of saved tasks and idempotency records.
    """
    payload = task_create_payload.model_dump(mode="json")
    other_payload = {**payload, "title": "Another task"} if scenario == "different_body" else payload.copy()
    key = uuid4()
    other_key = uuid4() if scenario == "different_keys" else key
    requests = [(key, payload), (other_key, other_payload)]

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        async with asyncio.timeout(TIMEOUT_SECONDS), asyncio.TaskGroup() as group, concurrent_db() as blocker:
            repository = IdempotencySqlAlchemyRepository(blocker)
            for request_key in {key, other_key}:
                await repository.lock_by_scope_key(operation_scope, request_key)
            blocker_pid = await blocker.scalar(select(func.pg_backend_pid()))
            assert isinstance(blocker_pid, int)

            pending = [
                group.create_task(client.post(ENDPOINT, json=body, headers={"Idempotency-Key": str(request_key)}))
                for request_key, body in requests
            ]
            await wait_for_both_requests(blocker, blocker_pid)
            await blocker.rollback()

        responses = [request.result() for request in pending]
        assert sorted(response.status_code for response in responses) == expected_status_codes, [
            response.text for response in responses
        ]
        successful = [response for response in responses if response.status_code == status.HTTP_201_CREATED]
        assert len({response.json()["id"] for response in successful}) == expected_count
        if scenario == "same_request":
            assert responses[0].json() == responses[1].json()

        for response in responses:
            if response.status_code == status.HTTP_409_CONFLICT:
                assert response.json()["detail"] == str(IdempotencyDifferentRequestError())

        async with concurrent_db() as session:
            tasks = list(await session.scalars(select(Task).where(Task.author_id == stub_claims.sub)))
            records = list(await session.scalars(select(Idempotency).where(Idempotency.scope == operation_scope)))
        assert len(tasks) == len(records) == expected_count
        assert {str(task.id) for task in tasks} == {response.json()["id"] for response in successful}
        for task in tasks:
            record = next(record for record in records if record.response_body["id"] == str(task.id))
            assert record.status_code == status.HTTP_201_CREATED
            assert TaskResponseScheme.model_validate(task) == TaskResponseScheme.model_validate(record.response_body)

        for (request_key, body), response in zip(requests, responses, strict=True):
            if response.status_code == status.HTTP_201_CREATED:
                assert TaskCreatePayloadScheme.model_validate(response.json()).model_dump(mode="json") == body
                replay = await client.post(ENDPOINT, json=body, headers={"Idempotency-Key": str(request_key)})
                assert replay.status_code == status.HTTP_201_CREATED, replay.text
                assert replay.json() == response.json()

        async with concurrent_db() as session:
            task_count = await session.scalar(
                select(func.count()).select_from(Task).where(Task.author_id == stub_claims.sub)
            )
            assert isinstance(task_count, int)
            assert task_count == expected_count

            record_count = await session.scalar(
                select(func.count()).select_from(Idempotency).where(Idempotency.scope == operation_scope)
            )
            assert isinstance(record_count, int)
            assert record_count == expected_count
