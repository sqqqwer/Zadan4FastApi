from collections.abc import AsyncIterator, Callable
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.dependencies.event_bus import get_event_bus
from src.core.dependencies.idempotency import get_idempotency_service
from src.core.dependencies.jwt import get_current_claims
from src.core.events.bus import AbstractEventsBus
from src.core.main import app
from src.core.schemas.token_claims import AccessTokenClaims
from src.core.services.idempotency import IdempotencyAbstractService
from src.modules.org.dependencies.user_directory import get_local_user_directory as org_get_local_user_directory
from src.modules.org.schemas import StructCreateScheme
from tests.stubs import StubOrgUserDirectory

from .constants import COMPANY_ID, STRUCT_NAME
from .stubs import stub_get_current_claims


@pytest.fixture(autouse=True)
def enable_test_db(test_db):
    """Enable the test database fixture for each test.

    Args:
        test_db: Database session used by the test.
    """

@pytest.fixture
async def get_async_client() -> AsyncIterator[AsyncClient]:
    """Get an async HTTP client for the test application.

    Yields:
        AsyncClient: HTTP client for sending requests to the application.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client

@pytest.fixture(autouse=True)
def mock_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncMock:
    """Override the idempotency service with a mock that allows every operation.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AsyncMock: Mock idempotency service that does not save records.
    """
    service = AsyncMock(spec=IdempotencyAbstractService)
    service.check_operation.return_value = None

    dependency: Callable[..., Any] = get_idempotency_service
    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: service,
    )

    return service

@pytest.fixture
def stub_org_user_directory(
    monkeypatch: pytest.MonkeyPatch
) -> StubOrgUserDirectory:
    """Override the org user directory with a stub.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        StubOrgUserDirectory: Stub org user directory.
    """
    directory = StubOrgUserDirectory(
        company_id=UUID(COMPANY_ID)
    )

    dependency: Callable[..., Any] = org_get_local_user_directory
    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: directory,
    )

    return directory

@pytest.fixture
def stub_claims(
    monkeypatch: pytest.MonkeyPatch
) -> AccessTokenClaims:
    """Override the current user claims with test admin claims.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AccessTokenClaims: Test admin claims.
    """
    claims = stub_get_current_claims()

    dependency: Callable[..., Any] = get_current_claims

    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: claims,
    )

    return claims

@pytest.fixture
def mock_event_bus(
    monkeypatch: pytest.MonkeyPatch
) -> AsyncMock:
    """Override the event bus with a mock.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AsyncMock: Mock event bus.
    """
    bus = AsyncMock(spec=AbstractEventsBus)

    dependency: Callable[..., Any] = get_event_bus

    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: bus,
    )

    return bus

@pytest.fixture
def struct_create_payload() -> StructCreateScheme:
    """Create struct data for the test request.

    Returns:
        StructCreateScheme: Struct creation data.
    """
    return StructCreateScheme(
        name=STRUCT_NAME
    )
