from uuid import UUID

from fastapi import APIRouter, status
from pydantic import EmailStr

from src.core.dependencies.idempotency import IdempotencyServiceDependency
from src.core.dependencies.jwt import AccessTokenClaimsDependency, RequireAdminClaimsDependency
from src.core.dependencies.pagination import PaginationDependency

from ...dependencies.services import AuthServiceDependency, RegistrationServiceDependency, UserServiceDependency
from ...schemas import (
    AccountEmail,
    AccountEmailResponse,
    CompanySignUpEmailConfirmation,
    LoginScheme,
    RefreshToken,
    TokenResponse,
    UserAdminAndCompanyRegistration,
    UserAdminAndCompanyRegistrationResponse,
    UserEmployeeRegistration,
    UserEmployeeRegistrationResponse,
    UserRegistration,
    UserResponse,
    UserScheme,
)

router = APIRouter(prefix="/auth/api/v1")


@router.post("/check-account/{account_email}")
async def check_account_email(
    account_email: EmailStr,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> None:
    """Check that the email is available and create a registration invite.

    Args:
        account_email: Account email to check.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    await service.check_account_email(account_email=account_email, idempotency=idempotency)


@router.post("/sign-up")
async def company_sign_up_email_confirmation(
    payload: CompanySignUpEmailConfirmation,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> AccountEmailResponse:
    """Confirm the company registration email and create an account.

    Args:
        payload: Email and invite token for confirmation.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Returns:
        AccountEmailResponse: Account ID and email.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.company_sign_up_email_confirmation(payload=payload, idempotency=idempotency)


@router.post(
    "/sign-up-complete",
    status_code=status.HTTP_201_CREATED,
)
async def create_company_and_admin(
    payload: UserAdminAndCompanyRegistration,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> UserAdminAndCompanyRegistrationResponse:
    """Create a company and its admin user.

    Args:
        payload: Company and admin registration data.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Returns:
        UserAdminAndCompanyRegistrationResponse: Created company and admin data.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.create_company_and_admin(payload=payload, idempotency=idempotency)


@router.post(
    "/company/add-employee",
    status_code=status.HTTP_201_CREATED,
)
async def create_user_employee_start(
    payload: UserEmployeeRegistration,
    claims: RequireAdminClaimsDependency,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> UserEmployeeRegistrationResponse:
    """Create an employee account and a registration invite.

    Args:
        payload: Employee email and name data.
        claims: Access token claims of the current admin.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Returns:
        UserEmployeeRegistrationResponse: Employee data with the invite token and link.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.create_user_employee_start(
        payload=payload, company_id=claims.company_id, idempotency=idempotency
    )


@router.post("/employee-invite/{invite_token}")
async def create_user_employee_complete(
    invite_token: str,
    payload: UserRegistration,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> UserResponse:
    """Complete employee registration using an invite token.

    Args:
        invite_token: Raw invite token.
        payload: Employee registration data.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Returns:
        UserResponse: User response data.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.create_user_employee_complete(
        payload=payload, invite_token=invite_token, idempotency=idempotency
    )


@router.post("/email-change")
async def change_email_start(
    payload: AccountEmail,
    claims: AccessTokenClaimsDependency,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> None:
    """Create an invite to confirm an account email change.

    Args:
        payload: Account email data.
        claims: Current user access token claims.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    await service.change_email_start(payload=payload, user_id=claims.sub, idempotency=idempotency)


@router.post("/email-change-complete/{token}")
async def change_email_complete(
    token: str,
    claims: AccessTokenClaimsDependency,
    service: RegistrationServiceDependency,
    idempotency: IdempotencyServiceDependency,
) -> AccountEmailResponse:
    """Confirm and update the account email.

    Args:
        token: Raw email change token.
        claims: Current user access token claims.
        service: Registration service.
        idempotency: Service for checking and saving idempotent operations.

    Returns:
        AccountEmailResponse: Account ID and email.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.change_email_complete(token=token, user_id=claims.sub, idempotency=idempotency)


@router.put("/users/me")
async def update_user(
    payload: UserScheme, claims: AccessTokenClaimsDependency, service: UserServiceDependency
) -> UserResponse:
    """Update the user.

    Args:
        payload: User first and last names.
        claims: Current user access token claims.
        service: User service.

    Returns:
        UserResponse: User response data.
    """
    return await service.update_user(user_id=claims.sub, payload=payload)


@router.get("/users/me")
async def get_user_me(claims: AccessTokenClaimsDependency, service: UserServiceDependency) -> UserResponse:
    """Get the current user.

    Args:
        claims: Current user access token claims.
        service: User service.

    Returns:
        UserResponse: User response data.
    """
    return await service.get_user(user_id=claims.sub, current_company_id=claims.company_id)


@router.get("/users/{user_id}")
async def get_user(user_id: UUID, claims: AccessTokenClaimsDependency, service: UserServiceDependency) -> UserResponse:
    """Get the user.

    Args:
        user_id: User ID.
        claims: Current user access token claims.
        service: User service.

    Returns:
        UserResponse: User response data.
    """
    return await service.get_user(user_id=user_id, current_company_id=claims.company_id)


@router.get("/company/employees")
async def get_company_users(
    service: UserServiceDependency, claims: AccessTokenClaimsDependency, pagination: PaginationDependency
) -> list[UserResponse]:
    """Get a list of users in the current company.

    Args:
        service: User service.
        claims: Current user access token claims.
        pagination: Pagination limit and offset.

    Returns:
        list[UserResponse]: List of user responses.
    """
    return await service.get_users_in_company(
        company_id=claims.company_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("/login")
async def login(payload: LoginScheme, service: AuthServiceDependency) -> TokenResponse:
    """Log in using an email and password.

    Args:
        payload: Account email and password.
        service: Auth service.

    Returns:
        TokenResponse: Access and refresh tokens with expiration data.
    """
    return await service.login(payload=payload)


@router.post("/login-refresh")
async def login_refresh(payload: RefreshToken, service: AuthServiceDependency) -> TokenResponse:
    """Get a new access token using the refresh token.

    Args:
        payload: Refresh token.
        service: Auth service.

    Returns:
        TokenResponse: Access and refresh tokens with expiration data.
    """
    return await service.refresh_login(payload=payload)
