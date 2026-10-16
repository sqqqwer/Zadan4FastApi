from typing import Any
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from src.modules.auth.schemas import CompanySignUpEmailConfirmation

from .constants import ADMIN_EMAIL


@pytest.mark.parametrize(
    argnames=["account_email_state", "expected_status_code"],
    argvalues=[
        ("available", status.HTTP_200_OK),
        ("already_exists", status.HTTP_409_CONFLICT),
    ],
    indirect=["account_email_state"],
)
async def test_check_account_email(
    get_async_client: AsyncClient,
    account_email_state: None,
    expected_status_code: int,
):
    """Check HTTP statuses for available and already registered emails.

    Args:
        get_async_client: Async HTTP client for the test application.
        account_email_state: Prepared account state in the test database.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.post(
        f"/auth/api/v1/check-account/{ADMIN_EMAIL}",
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == expected_status_code, response.text


@pytest.mark.parametrize(
    argnames=["email_confirmation_state", "expected_status_code"],
    argvalues=[
        ("valid", status.HTTP_200_OK),
        ("not_found", status.HTTP_404_NOT_FOUND),
        ("expired", status.HTTP_400_BAD_REQUEST),
        ("wrong_purpose", status.HTTP_400_BAD_REQUEST),
        ("already_used", status.HTTP_409_CONFLICT),
        ("wrong_recipient", status.HTTP_400_BAD_REQUEST),
        ("account_already_exists", status.HTTP_409_CONFLICT),
    ],
    indirect=["email_confirmation_state"],
)
async def test_company_sign_up_email_confirmation(
    get_async_client: AsyncClient,
    email_confirmation_state: None,
    company_sign_up_email_confirmation_payload: CompanySignUpEmailConfirmation,
    expected_status_code: int,
):
    """Check HTTP statuses for email confirmation with different invite states.

    Args:
        get_async_client: Async HTTP client for the test application.
        email_confirmation_state: Prepared invite and account state in the test database.
        company_sign_up_email_confirmation_payload: Email confirmation data.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.post(
        "/auth/api/v1/sign-up",
        json=company_sign_up_email_confirmation_payload.model_dump(mode="json", by_alias=True),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == expected_status_code, response.text


@pytest.mark.parametrize(
    argnames=["company_registration_data", "expected_status_code"],
    argvalues=[
        ("valid", status.HTTP_201_CREATED),
        ("company_already_exists", status.HTTP_409_CONFLICT),
        ("account_not_found", status.HTTP_404_NOT_FOUND),
        ("secrets_already_exist", status.HTTP_409_CONFLICT),
    ],
    indirect=["company_registration_data"],
)
async def test_create_company_and_admin(
    get_async_client: AsyncClient,
    company_registration_data: dict[str, Any],
    expected_status_code: int,
):
    """Check HTTP statuses for company registration with a confirmed session.

    Args:
        get_async_client: Async HTTP client for the test application.
        company_registration_data: Company registration request body.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.post(
        "/auth/api/v1/sign-up-complete",
        json=company_registration_data,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == expected_status_code, response.text
