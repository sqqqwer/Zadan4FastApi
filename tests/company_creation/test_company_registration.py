import datetime
from unittest.mock import AsyncMock

import pytest

from src.core.resources.enums import RoleEnum
from src.modules.auth.models import Account, Company, Invite, Secrets
from src.modules.auth.resources.enums import InvitePurposeEnum
from src.modules.auth.resources.exceptions import (
    AccountNotFound,
    AccountWithEmailAlreadyExists,
    CompanyWithThisNameAlreadyExists,
    InviteAlreadyUsed,
    InviteExpired,
    InviteNotFound,
    InviteNotMatchingEmailWithAccount,
    InviteWrongPurpose,
    UserWithThisAccountAlreadyExists,
)
from src.modules.auth.schemas import CompanySignUpEmailConfirmation, UserAdminAndCompanyRegistration
from src.modules.auth.services.password_service import PasswordService
from src.modules.auth.services.registration_service import RegistrationService
from tests.company_creation.repositories import FakeDatabase

from .constants import (
    ADMIN_EMAIL,
    WRONG_ADMIN_EMAIL,
    WRONG_INVITE_TOKEN_HASH,
)


async def test_check_account_email(
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an available email gets a company registration invite.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    await registration_service.check_account_email(
        account_email=ADMIN_EMAIL,
        idempotency=mock_idempotency
    )

    assert len(fake_db.invites) == 1

    invite = next(iter(fake_db.invites.values()))

    mock_uow.commit.assert_awaited_once()
    assert invite.recipient_email == ADMIN_EMAIL
    assert invite.purpose == InvitePurposeEnum.COMPANY_REGISTRATION


async def test_check_account_email_already_exists(
    new_account: Account,
    fake_db: FakeDatabase,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an existing account email is rejected.

    Args:
        new_account: Account created for the test.
        fake_db: Fake database used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    with pytest.raises(AccountWithEmailAlreadyExists):
        await registration_service.check_account_email(
            account_email=ADMIN_EMAIL,
            idempotency=mock_idempotency,
        )

    assert len(fake_db.invites) == 0


async def test_company_sign_up_email_confirmation(  # noqa: PLR0913, PLR0917
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that email confirmation creates an account and uses the invite.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    payload = company_sign_up_email_confirmation_payload
    response = await registration_service.company_sign_up_email_confirmation(
        payload=payload,
        idempotency=mock_idempotency,
    )

    assert len(fake_db.accounts) == 1

    account = fake_db.accounts[response.id]

    mock_uow.commit.assert_awaited_once()
    assert new_invite_company_registration.used_at is not None
    assert account.email == payload.email
    assert response.email == payload.email


async def test_company_sign_up_email_confirmation_invite_not_found(
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an unknown invite token is rejected.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    new_invite_company_registration.token_hash = WRONG_INVITE_TOKEN_HASH
    with pytest.raises(InviteNotFound):
        await registration_service.company_sign_up_email_confirmation(
            payload=company_sign_up_email_confirmation_payload,
            idempotency=mock_idempotency,
        )


async def test_company_sign_up_email_confirmation_invite_expired(
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an expired invite is rejected.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    new_invite_company_registration.expired_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    with pytest.raises(InviteExpired):
        await registration_service.company_sign_up_email_confirmation(
            payload=company_sign_up_email_confirmation_payload,
            idempotency=mock_idempotency,
        )


async def test_company_sign_up_email_confirmation_invite_wrong_purpose(
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an invite with the wrong purpose is rejected.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    new_invite_company_registration.purpose = InvitePurposeEnum.EMAIL_CHANGE
    with pytest.raises(InviteWrongPurpose):
        await registration_service.company_sign_up_email_confirmation(
            payload=company_sign_up_email_confirmation_payload,
            idempotency=mock_idempotency,
        )


async def test_company_sign_up_email_confirmation_invite_already_used(
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that a used invite is rejected.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    new_invite_company_registration.used_at = datetime.datetime.now(datetime.UTC)
    with pytest.raises(InviteAlreadyUsed):
        await registration_service.company_sign_up_email_confirmation(
            payload=company_sign_up_email_confirmation_payload,
            idempotency=mock_idempotency,
        )

async def test_company_sign_up_email_confirmation_invite_wrong_recipient(
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an invite for a different email is rejected.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    new_invite_company_registration.recipient_email = WRONG_ADMIN_EMAIL
    with pytest.raises(InviteNotMatchingEmailWithAccount):
        await registration_service.company_sign_up_email_confirmation(
            payload=company_sign_up_email_confirmation_payload,
            idempotency=mock_idempotency,
        )

async def test_company_sign_up_email_confirmation_account_already_exists(
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    new_invite_company_registration: Invite,
    new_account: Account,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that email confirmation rejects an existing account.

    Args:
        company_sign_up_email_confirmation_payload: Email confirmation data used by the test.
        new_invite_company_registration: Company registration invite used by the test.
        new_account: Account created for the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    with pytest.raises(AccountWithEmailAlreadyExists):
        await registration_service.company_sign_up_email_confirmation(
            payload=company_sign_up_email_confirmation_payload,
            idempotency=mock_idempotency,
        )

async def test_create_company_and_admin(  # noqa: PLR0913, PLR0917
    new_account: Account,
    fake_db: FakeDatabase,
    user_admin_and_company_registration_payload: UserAdminAndCompanyRegistration,
    mock_uow: AsyncMock,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that a company, admin, membership, and password are created.

    Args:
        new_account: Account created for the test.
        fake_db: Fake database used by the test.
        user_admin_and_company_registration_payload: Company and admin registration data used by the test.
        mock_uow: Mock unit of work.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    payload = user_admin_and_company_registration_payload
    response = await registration_service.create_company_and_admin(
        payload=payload,
        idempotency=mock_idempotency,
    )

    assert len(fake_db.users) == 1
    assert len(fake_db.companies) == 1
    assert len(fake_db.members) == 1
    assert len(fake_db.secrets) == 1

    user = fake_db.users[response.user_id]
    company = fake_db.companies[response.company_id]
    membership = user.membership
    secrets = new_account.secrets

    mock_uow.commit.assert_awaited_once()

    assert secrets is not None
    assert secrets.password_hash is not None

    assert company.name == payload.company_name
    assert user.first_name == payload.first_name
    assert user.last_name == payload.last_name

    assert membership.company_id == company.id
    assert membership.user_id == user.id
    assert membership.role == RoleEnum.ADMIN

    assert secrets.user_id == user.id
    assert secrets.account_id == new_account.id

    assert PasswordService().password_verify(
        payload.password,
        secrets.password_hash,
    )


async def test_create_company_and_admin_company_already_exists(
    new_account: Account,
    new_company: Company,
    user_admin_and_company_registration_payload: UserAdminAndCompanyRegistration,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that an existing company name is rejected.

    Args:
        new_account: Account created for the test.
        new_company: Company created for the test.
        user_admin_and_company_registration_payload: Company and admin registration data used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    with pytest.raises(CompanyWithThisNameAlreadyExists):
        await registration_service.create_company_and_admin(
            payload=user_admin_and_company_registration_payload,
            idempotency=mock_idempotency,
        )


async def test_create_company_and_admin_account_not_found(
    user_admin_and_company_registration_payload: UserAdminAndCompanyRegistration,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that company registration rejects a missing account.

    Args:
        user_admin_and_company_registration_payload: Company and admin registration data used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    with pytest.raises(AccountNotFound):
        await registration_service.create_company_and_admin(
            payload=user_admin_and_company_registration_payload,
            idempotency=mock_idempotency,
        )

async def test_create_company_and_admin_account_secret_already_exists(
    new_secrets: Secrets,
    user_admin_and_company_registration_payload: UserAdminAndCompanyRegistration,
    registration_service: RegistrationService,
    mock_idempotency: AsyncMock,
):
    """Check that company registration rejects an account linked to a user.

    Args:
        new_secrets: Account secrets created for the test.
        user_admin_and_company_registration_payload: Company and admin registration data used by the test.
        registration_service: Registration service used by the test.
        mock_idempotency: Mock idempotency.
    """
    with pytest.raises(UserWithThisAccountAlreadyExists):
        await registration_service.create_company_and_admin(
            payload=user_admin_and_company_registration_payload,
            idempotency=mock_idempotency,
        )
