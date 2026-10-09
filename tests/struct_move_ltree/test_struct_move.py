from unittest.mock import AsyncMock
from uuid import UUID

from fastapi import status
from httpx import AsyncClient

from src.core.schemas.token_claims import AccessTokenClaims
from src.modules.org.schemas import StructCreateScheme
from tests.stubs import StubOrgUserDirectory

from .constants import STRUCT_NAME


async def test_struct_create(
    get_async_client: AsyncClient,
    mock_event_bus: AsyncMock,
    stub_claims: AccessTokenClaims,
    struct_create_payload: StructCreateScheme,
    stub_org_user_directory: StubOrgUserDirectory,
):
    """Check that a root struct is created and its saved data can be retrieved.

    Args:
        get_async_client: Async HTTP client for the test application.
        mock_event_bus: Mock event bus.
        stub_claims: Access token claims of the test admin.
        struct_create_payload: Struct creation data.
        stub_org_user_directory: Stub user directory for the org module.
    """
    client = get_async_client

    response = await client.post(
        "/org/api/v1/structs",
        json=struct_create_payload.model_dump(mode="json"),
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text

    data = response.json()

    assert data["name"] == STRUCT_NAME
    assert data["path"] == UUID(data["id"]).hex
    assert data["company_id"] == str(stub_claims.company_id)

    saved_response = await client.get(
        f"/org/api/v1/structs/{data["id"]}"
    )
    assert saved_response.status_code == status.HTTP_200_OK, saved_response.text
    assert saved_response.json() == data


async def test_struct_move_to_struct(
    get_async_client: AsyncClient,
    mock_event_bus: AsyncMock,
    stub_claims: AccessTokenClaims,
    stub_org_user_directory: StubOrgUserDirectory,
):
    """Check that moving a struct updates its path and the paths of its children.

    Args:
        get_async_client: Async HTTP client for the test application.
        mock_event_bus: Mock event bus.
        stub_claims: Access token claims of the test admin.
        stub_org_user_directory: Stub user directory for the org module.
    """
    client = get_async_client

    response_create_a = await client.post(
        "/org/api/v1/structs",
        json={"name": "A"},
    )
    assert response_create_a.status_code == status.HTTP_201_CREATED, response_create_a.text

    response_create_b = await client.post(
        "/org/api/v1/structs",
        json={"name": "B"},
    )
    assert response_create_b.status_code == status.HTTP_201_CREATED, response_create_b.text

    response_create_c = await client.post(
        "/org/api/v1/structs",
        json={"name": "C"},
    )
    assert response_create_c.status_code == status.HTTP_201_CREATED, response_create_c.text

    a_id = response_create_a.json()["id"]
    b_id = response_create_b.json()["id"]
    c_id = response_create_c.json()["id"]
    a_label = UUID(a_id).hex
    b_label = UUID(b_id).hex
    c_label = UUID(c_id).hex


    response_move_c_to_b = await client.post(
        f"/org/api/v1/structs/{c_id}/move",
        json={"struct_id": b_id},
    )
    assert response_move_c_to_b.status_code == status.HTTP_204_NO_CONTENT, response_move_c_to_b.text

    response_c = await client.get(
        f"/org/api/v1/structs/{c_id}",
    )
    assert response_c.status_code == status.HTTP_200_OK, response_c.text
    assert response_c.json()["path"] == f"{b_label}.{c_label}"


    response_move_b_to_a = await client.post(
        f"/org/api/v1/structs/{b_id}/move",
        json={"struct_id": a_id},
    )
    assert response_move_b_to_a.status_code == status.HTTP_204_NO_CONTENT, response_move_b_to_a.text

    expected_structs = [
        (a_id, "A", a_label),
        (b_id, "B", f"{a_label}.{b_label}"),
        (c_id, "C", f"{a_label}.{b_label}.{c_label}"),
    ]
    for struct_id, name, path in expected_structs:
        saved_response = await client.get(f"/org/api/v1/structs/{struct_id}")
        assert saved_response.status_code == status.HTTP_200_OK, saved_response.text
        saved_data = saved_response.json()
        assert saved_data["id"] == struct_id
        assert saved_data["name"] == name
        assert saved_data["path"] == path
        assert saved_data["company_id"] == str(stub_claims.company_id)

    response_a_tree = await client.get(
        f"/org/api/v1/structs/{a_id}/tree"
    )

    assert response_a_tree.status_code == status.HTTP_200_OK, response_a_tree.text

    tree = response_a_tree.json()
    assert tree["id"] == a_id
    assert tree["path"] == a_label
    children = tree["child_paths"]
    expected_child_count = 2

    assert len(children) == expected_child_count
    assert {"name": "B", "path": f"{a_label}.{b_label}"} in children
    assert {"name": "C", "path": f"{a_label}.{b_label}.{c_label}"} in children


async def test_struct_move_to_himself(
    get_async_client: AsyncClient,
    mock_event_bus: AsyncMock,
    stub_claims: AccessTokenClaims,
    stub_org_user_directory: StubOrgUserDirectory,
):
    """Check that moving a struct into itself is rejected without changing its data.

    Args:
        get_async_client: Async HTTP client for the test application.
        mock_event_bus: Mock event bus.
        stub_claims: Access token claims of the test admin.
        stub_org_user_directory: Stub user directory for the org module.
    """
    client = get_async_client

    response_create_a = await client.post(
        "/org/api/v1/structs",
        json={"name": "A"},
    )
    assert response_create_a.status_code == status.HTTP_201_CREATED, response_create_a.text

    a_data = response_create_a.json()
    a_id = a_data["id"]

    response_move_a_to_a = await client.post(
        f"/org/api/v1/structs/{a_id}/move",
        json={"struct_id": a_id},
    )
    assert response_move_a_to_a.status_code == status.HTTP_409_CONFLICT, response_move_a_to_a.text

    saved_response = await client.get(
        f"/org/api/v1/structs/{a_id}",
    )
    assert saved_response.status_code == status.HTTP_200_OK, saved_response.text
    assert saved_response.json() == a_data


async def test_struct_move_to_descendant(
    get_async_client: AsyncClient,
    mock_event_bus: AsyncMock,
    stub_claims: AccessTokenClaims,
    stub_org_user_directory: StubOrgUserDirectory,
):
    """Check that moving a struct into its descendant is rejected without changing the tree.

    Args:
        get_async_client: Async HTTP client for the test application.
        mock_event_bus: Mock event bus.
        stub_claims: Access token claims of the test admin.
        stub_org_user_directory: Stub user directory for the org module.
    """
    client = get_async_client

    response_create_a = await client.post(
        "/org/api/v1/structs",
        json={"name": "A"},
    )
    assert response_create_a.status_code == status.HTTP_201_CREATED, response_create_a.text

    response_create_b = await client.post(
        "/org/api/v1/structs",
        json={"name": "B"},
    )
    assert response_create_b.status_code == status.HTTP_201_CREATED, response_create_b.text

    response_create_c = await client.post(
        "/org/api/v1/structs",
        json={"name": "C"},
    )
    assert response_create_c.status_code == status.HTTP_201_CREATED, response_create_c.text

    a_id = response_create_a.json()["id"]
    b_id = response_create_b.json()["id"]
    c_id = response_create_c.json()["id"]
    a_label = UUID(a_id).hex
    b_label = UUID(b_id).hex
    c_label = UUID(c_id).hex

    response_move_b_to_a = await client.post(
        f"/org/api/v1/structs/{b_id}/move",
        json={"struct_id": a_id},
    )
    assert response_move_b_to_a.status_code == status.HTTP_204_NO_CONTENT, response_move_b_to_a.text

    response_move_c_to_b = await client.post(
        f"/org/api/v1/structs/{c_id}/move",
        json={"struct_id": b_id},
    )
    assert response_move_c_to_b.status_code == status.HTTP_204_NO_CONTENT, response_move_c_to_b.text

    response_move_a_to_c = await client.post(
        f"/org/api/v1/structs/{a_id}/move",
        json={"struct_id": c_id},
    )
    assert response_move_a_to_c.status_code == status.HTTP_409_CONFLICT, response_move_a_to_c.text

    expected_structs = [
        (a_id, "A", a_label),
        (b_id, "B", f"{a_label}.{b_label}"),
        (c_id, "C", f"{a_label}.{b_label}.{c_label}"),
    ]
    for struct_id, name, path in expected_structs:
        saved_response = await client.get(f"/org/api/v1/structs/{struct_id}")
        assert saved_response.status_code == status.HTTP_200_OK, saved_response.text
        saved_data = saved_response.json()
        assert saved_data["id"] == struct_id
        assert saved_data["name"] == name
        assert saved_data["path"] == path
        assert saved_data["company_id"] == str(stub_claims.company_id)
