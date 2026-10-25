import datetime
import hashlib
from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.main import app
from src.core.request_context import correlation_id_var
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract
from src.modules.auth.models import Account, Company, Invite, Secrets, User
from src.modules.auth.resources.enums import InvitePurposeEnum
from src.modules.auth.schemas import (
    AccountEmail,
    CompanyName,
    CompanySignUpEmailConfirmation,
    InviteCreation,
    UserAdminAndCompanyRegistration,
    UserScheme,
)
from src.modules.auth.services.auth_service import AuthService
from src.modules.auth.services.jwt_service import AbstractJWTEncoderService
from src.modules.auth.services.password_service import PasswordService
from src.modules.auth.services.registration_service import RegistrationService
from src.modules.auth.services.registration_session_service import RegistrationSessionService
from src.modules.auth.services.user_service import UserService
from src.shared.outbox.repository import OutboxAbstractRepository
from tests.company_creation.repositories import (
    AccountMockRepository,
    CompanyMockRepository,
    FakeDatabase,
    RefreshSessionMockRepository,
    UserMockRepository,
)

from .constants import (
    ADMIN_EMAIL,
    ADMIN_FIRST_NAME,
    ADMIN_LAST_NAME,
    COMPANY_NAME,
    INVITE_TOKEN,
    JWT_ACCESS_TOKEN,
    PASSWORD,
    REGISTRATION_TOKEN,
    WRONG_ADMIN_EMAIL,
    WRONG_INVITE_TOKEN_HASH,
)


@pytest.fixture
def fake_db() -> FakeDatabase:
    """Create a fake database for tests.

    Returns:
        FakeDatabase: Fake database.
    """
    return FakeDatabase()


@pytest.fixture
def mock_uow() -> AsyncMock:
    """Create a mock unit of work.

    Returns:
        AsyncMock: Mock unit of work.
    """
    return AsyncMock(spec=UowAbstract)


@pytest.fixture
def mock_outbox_repository() -> AsyncMock:
    """Create a mock outbox repository.

    Returns:
        AsyncMock: Mock outbox repository.
    """
    return AsyncMock(spec=OutboxAbstractRepository)

@pytest.fixture
def mock_idempotency() -> AsyncMock:
    """Create a mock idempotency service.

    Returns:
        AsyncMock: Mock idempotency.
    """
    service = AsyncMock(spec=IdempotencyAbstractService)
    service.check_operation.return_value = None
    return service

@pytest.fixture(autouse=True)
def correlation_context() -> Iterator[None]:
    """Create a correlation id."""
    token = correlation_id_var.set(str(uuid4()))
    try:
        yield
    finally:
        correlation_id_var.reset(token)


@pytest.fixture
def mock_jwt_encoder_service() -> Mock:
    """Create a mock JWT encoder service.

    Returns:
        Mock: Mock JWT encoder service.
    """
    service = Mock(spec=AbstractJWTEncoderService)
    service.get_encoded_jwt.return_value = JWT_ACCESS_TOKEN
    return service


@pytest.fixture
def mock_registration_session_service() -> AsyncMock:
    """Create a mock registration session service.

    Returns:
        AsyncMock: Mock registration session service.
    """
    service = AsyncMock(spec=RegistrationSessionService)
    service.create.return_value = REGISTRATION_TOKEN
    return service


@pytest.fixture
def registration_service(
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    mock_outbox_repository: AsyncMock,
    mock_registration_session_service: AsyncMock,
) -> RegistrationService:
    """Create a registration service for tests.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_outbox_repository: Mock outbox repository.
        mock_registration_session_service: Mock registration session service.

    Returns:
        RegistrationService: Registration service.
    """
    return RegistrationService(
        account_repository=AccountMockRepository(fake_db),
        user_repository=UserMockRepository(fake_db),
        company_repository=CompanyMockRepository(fake_db),
        password_service=PasswordService(),
        registration_session_service=mock_registration_session_service,
        uow=mock_uow,
        outbox_repository=mock_outbox_repository,
    )


@pytest.fixture
def user_service(fake_db: FakeDatabase, mock_uow: AsyncMock) -> UserService:
    """Create a user service for tests.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.

    Returns:
        UserService: User service.
    """
    return UserService(
        user_repository=UserMockRepository(fake_db),
        company_repository=CompanyMockRepository(fake_db),
        uow=mock_uow,
    )


@pytest.fixture
def auth_service(fake_db: FakeDatabase, mock_uow: AsyncMock, mock_jwt_encoder_service: Mock) -> AuthService:
    """Create an auth service for tests.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_jwt_encoder_service: Mock JWT encoder service.

    Returns:
        AuthService: Auth service.
    """
    return AuthService(
        account_repository=AccountMockRepository(fake_db),
        refresh_session_repository=RefreshSessionMockRepository(fake_db),
        password_service=PasswordService(),
        jwt_encoder_service=mock_jwt_encoder_service,
        uow=mock_uow,
    )


@pytest.fixture
async def new_account(fake_db: FakeDatabase) -> Account:
    """Create account data for tests.

    Args:
        fake_db: Fake database used by the test.

    Returns:
        Account: Account object.
    """
    repository = AccountMockRepository(fake_db)
    scheme = AccountEmail(account=ADMIN_EMAIL)
    account = await repository.create_account(scheme)
    return account


@pytest.fixture
async def new_user(fake_db: FakeDatabase) -> User:
    """Create user data for tests.

    Args:
        fake_db: Fake database used by the test.

    Returns:
        User: User object.
    """
    repository = UserMockRepository(fake_db)
    scheme = UserScheme(first_name=ADMIN_FIRST_NAME, last_name=ADMIN_LAST_NAME)
    user = await repository.create_user(scheme)
    return user


@pytest.fixture
async def new_company(fake_db: FakeDatabase) -> Company:
    """Create company data for tests.

    Args:
        fake_db: Fake database used by the test.

    Returns:
        Company: Company object.
    """
    repository = CompanyMockRepository(fake_db)
    scheme = CompanyName(company_name=COMPANY_NAME)
    company = await repository.create_company(scheme)
    return company


@pytest.fixture
async def new_secrets(
    fake_db: FakeDatabase,
    new_account: Account,
    new_user: User,
) -> Secrets:
    """Create secrets data for tests.

    Args:
        fake_db: Fake database used by the test.
        new_account: Account created for the test.
        new_user: User created for the test.

    Returns:
        Secrets: Account secrets.
    """
    repository = AccountMockRepository(fake_db)
    password_service = PasswordService()
    raw_password = SecretStr(PASSWORD)
    secrets = await repository.create_secrets(
        user=new_user, account=new_account, hashed_password=password_service.password_hash(raw_password)
    )
    return secrets


@pytest.fixture
async def new_invite(fake_db: FakeDatabase) -> Invite:
    """Create invite data for tests.

    Args:
        fake_db: Fake database used by the test.

    Returns:
        Invite: Invite object.
    """
    repository = AccountMockRepository(fake_db)
    raw_token = INVITE_TOKEN
    scheme = InviteCreation(
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        recipient_email=ADMIN_EMAIL,
        expired_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
        purpose=InvitePurposeEnum.EMAIL_CHANGE,
    )
    invite = await repository.create_invite(scheme)
    return invite


@pytest.fixture
def new_invite_company_registration(new_invite: Invite) -> Invite:
    """Set the invite purpose to company registration.

    Args:
        new_invite: Invite created for the test.

    Returns:
        Invite: Invite object.
    """
    new_invite.purpose = InvitePurposeEnum.COMPANY_REGISTRATION
    return new_invite


@pytest.fixture
def company_sign_up_email_confirmation_payload() -> CompanySignUpEmailConfirmation:
    """Create email confirmation data for tests.

    Returns:
        CompanySignUpEmailConfirmation: Email confirmation data.
    """
    return CompanySignUpEmailConfirmation(invite_token=INVITE_TOKEN, account=ADMIN_EMAIL)


@pytest.fixture
def user_admin_and_company_registration_payload() -> UserAdminAndCompanyRegistration:
    """Create company and admin registration data for tests.

    Returns:
        UserAdminAndCompanyRegistration: Company and admin registration data.
    """
    return UserAdminAndCompanyRegistration.model_validate(
        {
            "company_name": COMPANY_NAME,
            "pass": PASSWORD,
            "first_name": ADMIN_FIRST_NAME,
            "last_name": ADMIN_LAST_NAME,
            "account": ADMIN_EMAIL,
        }
    )


@pytest.fixture
async def get_async_client(
    test_db: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    """Get an async HTTP client connected to the test database.

    Args:
        test_db: Database session used by the test.

    Yields:
        AsyncClient: HTTP client for sending requests to the application.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        yield client




@pytest.fixture
async def registration_invites(test_db: AsyncSession) -> list[Invite]:
    """Create registration invites for the owner and another account.

    Args:
        test_db: Database session used by the test.

    Returns:
        list[Invite]: Company registration invites saved in the test database.
    """
    invites = [
        Invite(
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            recipient_email=email,
            expired_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
            purpose=InvitePurposeEnum.COMPANY_REGISTRATION,
        )
        for email, raw_token in (
            (ADMIN_EMAIL, INVITE_TOKEN),
            (WRONG_ADMIN_EMAIL, f"{INVITE_TOKEN}_other"),
        )
    ]
    test_db.add_all(invites)
    await test_db.commit()

    return invites


@pytest.fixture
async def account_email_state(request: pytest.FixtureRequest, test_db: AsyncSession) -> None:
    """Prepare an available or already registered email.

    Args:
        request: Pytest request containing the selected test parameter.
        test_db: Database session used by the test.
    """
    if request.param == "already_exists":
        test_db.add(Account(email=ADMIN_EMAIL))
        await test_db.commit()


@pytest.fixture
async def email_confirmation_state(
    request: pytest.FixtureRequest,
    test_db: AsyncSession,
    registration_invites: list[Invite],
) -> None:
    """Prepare the invite and account for email confirmation.

    Args:
        request: Pytest request containing the selected test parameter.
        test_db: Database session used by the test.
        registration_invites: Registration invites saved in the test database.
    """
    invite = registration_invites[0]
    if request.param == "not_found":
        invite.token_hash = WRONG_INVITE_TOKEN_HASH
    elif request.param == "expired":
        invite.expired_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    elif request.param == "wrong_purpose":
        invite.purpose = InvitePurposeEnum.EMAIL_CHANGE
    elif request.param == "already_used":
        invite.used_at = datetime.datetime.now(datetime.UTC)
    elif request.param == "wrong_recipient":
        invite.recipient_email = WRONG_ADMIN_EMAIL
    elif request.param == "account_already_exists":
        test_db.add(Account(email=ADMIN_EMAIL))

    await test_db.commit()


@pytest.fixture
async def company_registration_data(  # noqa: PLR0913, PLR0917
    request: pytest.FixtureRequest,
    test_db: AsyncSession,
    get_async_client: AsyncClient,
    registration_invites: list[Invite],
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    user_admin_and_company_registration_payload: UserAdminAndCompanyRegistration,
) -> dict[str, Any]:
    """Confirm the email and prepare company registration data.

    Args:
        request: Pytest request containing the selected test parameter.
        test_db: Database session used by the test.
        get_async_client: Async HTTP client for the test application.
        registration_invites: Registration invites saved in the test database.
        company_sign_up_email_confirmation_payload: Email confirmation data.
        user_admin_and_company_registration_payload: Company and admin registration data.

    Returns:
        dict[str, Any]: Company registration request body.
    """
    response = await get_async_client.post(
        "/auth/api/v1/sign-up",
        json=company_sign_up_email_confirmation_payload.model_dump(mode="json", by_alias=True),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    payload = user_admin_and_company_registration_payload
    data = payload.model_dump(mode="json", by_alias=True)
    data["pass"] = payload.password.get_secret_value()

    if request.param == "company_already_exists":
        test_db.add(Company(name=payload.company_name))
    elif request.param == "account_not_found":
        data["account"] = WRONG_ADMIN_EMAIL
    elif request.param == "secrets_already_exist":
        test_db.add(Secrets(
            account_id=UUID(response.json()["id"]),
            user=User(first_name=ADMIN_FIRST_NAME, last_name=ADMIN_LAST_NAME),
            password_hash=PasswordService().password_hash(payload.password),
        ))

    await test_db.commit()
    return data
