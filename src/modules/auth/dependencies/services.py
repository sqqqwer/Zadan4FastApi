from typing import Annotated

from fastapi import Depends
from pydantic import SecretStr

from src.core.dependencies.event_bus import EventBusDependency
from src.core.dependencies.jwt import JwtSettingsDependency
from src.core.dependencies.uow import UowDependency

from ..services.auth_service import AuthService
from ..services.jwt_service import JWTEncoderService
from ..services.registration_service import RegistrationService
from ..services.user_service import UserService
from .password_hasher import PasswordHasherDependency
from .repositories import (
    AccountRepositoryDependency,
    CompanyRepositoryDependency,
    RefreshSessionRepositoryDependency,
    UserRepositoryDependency,
)


def get_jwt_encoder_service(settings: JwtSettingsDependency) -> JWTEncoderService:
    """Get the JWT encoder service.

    Args:
        settings: Application settings.

    Returns:
        JWTEncoderService: JWT encoder service.
    """
    return JWTEncoderService(
        secret_key=SecretStr(settings.jwt_private_key_path.read_text(encoding="utf-8")),
        algorithm=settings.jwt_algorithm,
    )


JWTEcoderServiceDependency = Annotated[JWTEncoderService, Depends(get_jwt_encoder_service)]


def get_registration_service(  # noqa: PLR0913, PLR0917
    account_repository: AccountRepositoryDependency,
    user_repository: UserRepositoryDependency,
    company_repository: CompanyRepositoryDependency,
    password_service: PasswordHasherDependency,
    uow: UowDependency,
    event_bus: EventBusDependency,
) -> RegistrationService:
    """Get the registration service.

    Args:
        account_repository: Database repository for account objects.
        user_repository: Database repository for user objects.
        company_repository: Database repository for company objects.
        password_service: Service for hashing and checking passwords.
        uow: Unit of work for database operations.
        event_bus: Event bus used to publish events.

    Returns:
        RegistrationService: Registration service.
    """
    return RegistrationService(
        account_repository=account_repository,
        user_repository=user_repository,
        company_repository=company_repository,
        password_service=password_service,
        uow=uow,
        event_bus=event_bus,
    )


def get_user_service(
    user_repository: UserRepositoryDependency,
    company_repository: CompanyRepositoryDependency,
    uow: UowDependency,
) -> UserService:
    """Get the user service.

    Args:
        user_repository: Database repository for user objects.
        company_repository: Database repository for company objects.
        uow: Unit of work for database operations.

    Returns:
        UserService: User service.
    """
    return UserService(user_repository=user_repository, company_repository=company_repository, uow=uow)


def get_auth_service(
    account_repository: AccountRepositoryDependency,
    refresh_session_repository: RefreshSessionRepositoryDependency,
    password_service: PasswordHasherDependency,
    jwt_encoder_service: JWTEcoderServiceDependency,
    uow: UowDependency,
) -> AuthService:
    """Get the auth service.

    Args:
        account_repository: Database repository for account objects.
        refresh_session_repository: Database repository for refresh session objects.
        password_service: Service for hashing and checking passwords.
        jwt_encoder_service: Service for encoding JWT access tokens.
        uow: Unit of work for database operations.

    Returns:
        AuthService: Auth service.
    """
    return AuthService(
        account_repository=account_repository,
        refresh_session_repository=refresh_session_repository,
        password_service=password_service,
        jwt_encoder_service=jwt_encoder_service,
        uow=uow,
    )


RegistrationServiceDependency = Annotated[RegistrationService, Depends(get_registration_service)]
UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
