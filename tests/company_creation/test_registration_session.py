import hashlib
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import Company, Invite, RegistrationSession, Secrets, User
from src.modules.auth.schemas import CompanySignUpEmailConfirmation, UserAdminAndCompanyRegistration
from src.modules.auth.services.constants import REGISTRATION_SESSION_ALIAS
from src.modules.auth.services.password_service import PasswordService

from .constants import INVITE_TOKEN, WRONG_ADMIN_EMAIL


@pytest.mark.parametrize("attacker_session", ["missing", "another_account"])
async def test_registration_cannot_be_hijacked(  # noqa: PLR0913, PLR0917
    attacker_session: str,
    get_async_client: AsyncClient,
    test_db: AsyncSession,
    registration_invites: list[Invite],
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    user_admin_and_company_registration_payload: UserAdminAndCompanyRegistration,
):
    """Reject registration takeover, let the owner finish, and reject session reuse.

    Args:
        attacker_session: Missing cookie or a session belonging to another account.
        get_async_client: Async HTTP client for the test application.
        test_db: Database session used by the test.
        registration_invites: Registration invites saved in the test database.
        company_sign_up_email_confirmation_payload: Owner's email confirmation data.
        user_admin_and_company_registration_payload: Company and admin registration data.
    """
    client = get_async_client
    payload = user_admin_and_company_registration_payload
    registration_data = user_admin_and_company_registration_payload.model_dump(mode="json", by_alias=True)
    registration_data["pass"] = payload.password.get_secret_value()

    confirmation_response = await client.post(
        "/auth/api/v1/sign-up",
        json=company_sign_up_email_confirmation_payload.model_dump(mode="json", by_alias=True),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert confirmation_response.status_code == status.HTTP_200_OK, confirmation_response.text

    account_id = UUID(confirmation_response.json()["id"])
    owner_token = client.cookies[REGISTRATION_SESSION_ALIAS]
    owner_token_hash = hashlib.sha256(owner_token.encode()).hexdigest()
    await test_db.refresh(registration_invites[0])
    assert registration_invites[0].used_at is not None


    client.cookies.clear()
    if attacker_session == "another_account":
        attacker_confirmation = await client.post(
            "/auth/api/v1/sign-up",
            json={"account": WRONG_ADMIN_EMAIL, "invite_token": f"{INVITE_TOKEN}_other"},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert attacker_confirmation.status_code == status.HTTP_200_OK, attacker_confirmation.text
        assert client.cookies[REGISTRATION_SESSION_ALIAS] != owner_token

    takeover_response = await client.post(
        "/auth/api/v1/sign-up-complete",
        json=registration_data,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert takeover_response.status_code == status.HTTP_401_UNAUTHORIZED, takeover_response.text
    assert await test_db.scalar(select(Secrets).where(Secrets.account_id == account_id)) is None
    assert await test_db.scalar(select(Company).where(Company.name == payload.company_name)) is None
    assert await test_db.scalar(select(User)) is None
    assert await test_db.scalar(
        select(RegistrationSession).where(RegistrationSession.token_hash == owner_token_hash)
    ) is not None

    client.cookies.clear()
    complete_response = await client.post(
        "/auth/api/v1/sign-up-complete",
        json=registration_data,
        headers={
            "Idempotency-Key": str(uuid4()),
            "Cookie": f"{REGISTRATION_SESSION_ALIAS}={owner_token}",
        },
    )
    assert complete_response.status_code == status.HTTP_201_CREATED, complete_response.text

    data = complete_response.json()
    saved_secrets = await test_db.scalar(select(Secrets).where(Secrets.account_id == account_id))
    assert saved_secrets is not None
    assert saved_secrets.password_hash is not None
    assert saved_secrets.user_id == UUID(data["user_id"])
    assert PasswordService().password_verify(payload.password, saved_secrets.password_hash)

    saved_company = await test_db.get(Company, UUID(data["company_id"]))
    assert saved_company is not None
    assert saved_company.name == payload.company_name
    assert await test_db.scalar(
        select(RegistrationSession).where(RegistrationSession.token_hash == owner_token_hash)
    ) is None

    replay_response = await client.post(
        "/auth/api/v1/sign-up-complete",
        json=registration_data,
        headers={
            "Idempotency-Key": str(uuid4()),
            "Cookie": f"{REGISTRATION_SESSION_ALIAS}={owner_token}",
        },
    )
    assert replay_response.status_code == status.HTTP_401_UNAUTHORIZED, replay_response.text
