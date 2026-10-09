from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic import BaseModel

from src.core.schemas.token_claims import AccessTokenClaims
from tests.stubs import StubOrgUserDirectory, StubTasksUserDirectory


@pytest.mark.parametrize(
    argnames=["endpoint_arg", "payload_arg", "expected_status_code"],
    argvalues=[
        pytest.param(
            "/auth/api/v1/check-account/{account_email}",
            None,
            status.HTTP_200_OK,
            id="invite_creation",
        ),
        pytest.param(
            "/org/api/v1/positions",
            "position_create_payload",
            status.HTTP_201_CREATED,
            id="position_create",
        ),
        pytest.param(
            "/org/api/v1/positions/{position_id}/user",
            "position_assign_user_payload",
            status.HTTP_204_NO_CONTENT,
            id="position_add_user",
        ),
        pytest.param(
            "/org/api/v1/structs",
            "struct_create_payload",
            status.HTTP_201_CREATED,
            id="struct_create",
        ),
        pytest.param(
            "/tasks/api/v1/tasks",
            "task_create_payload",
            status.HTTP_201_CREATED,
            id="task_create",
        ),
    ],
    indirect=["endpoint_arg", "payload_arg"]
)
async def test_param_idempotency_task_create(  # noqa: PLR0913, PLR0917
    endpoint_arg: str,
    payload_arg: BaseModel | None,
    expected_status_code: int,

    get_async_client: AsyncClient,
    idempotency_key: UUID,

    mock_event_bus: AsyncMock,
    stub_claims: AccessTokenClaims,
    stub_tasks_user_directory: StubTasksUserDirectory,
    stub_org_user_directory: StubOrgUserDirectory,
):
    """Check that repeated requests with the same idempotency key return the same response.

    Args:
        endpoint_arg: Endpoint URL for the test request.
        payload_arg: Request body, or None if no body is needed.
        expected_status_code: Expected HTTP status code for both requests.
        get_async_client: Async HTTP client for the test application.
        idempotency_key: Idempotency key shared by both requests.
        mock_event_bus: Mock event bus.
        stub_claims: Access token claims of the test admin.
        stub_tasks_user_directory: Stub user directory for the tasks module.
        stub_org_user_directory: Stub user directory for the org module.
    """
    client = get_async_client
    headers = {"Idempotency-Key": str(idempotency_key)}

    response1 = await client.post(
        endpoint_arg,
        json=payload_arg.model_dump(mode="json") if payload_arg else None,
        headers=headers,
    )
    response2 = await client.post(
        endpoint_arg,
        json=payload_arg.model_dump(mode="json") if payload_arg else None,
        headers=headers,
    )
    assert response1.status_code == expected_status_code, response1.text
    assert response2.status_code == expected_status_code, response2.text

    if expected_status_code == status.HTTP_204_NO_CONTENT:
        assert response1.content == response2.content == b""
    else:
        assert response1.json() == response2.json()
