import datetime
import hashlib
from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from src.core.events.bus import AbstractEventsBus
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
from src.modules.auth.services.user_service import UserService
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
def mock_event_bus() -> AsyncMock:
    """Create a mock event bus.

    Returns:
        AsyncMock: Mock event bus.
    """
    return AsyncMock(spec=AbstractEventsBus)

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
def registration_service(
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    mock_event_bus: AsyncMock
) -> RegistrationService:
    """Create a registration service for tests.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_event_bus: Mock event bus.

    Returns:
        RegistrationService: Registration service.
    """
    return RegistrationService(
        account_repository=AccountMockRepository(fake_db),
        user_repository=UserMockRepository(fake_db),
        company_repository=CompanyMockRepository(fake_db),
        password_service=PasswordService(),
        uow=mock_uow,
        event_bus=mock_event_bus,
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
