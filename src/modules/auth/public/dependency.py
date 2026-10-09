from typing import Annotated

from fastapi import Depends

from ..dependencies.repositories import CompanyRepositoryDependency, UserRepositoryDependency
from .service import AuthPublicService


def get_public_auth_service(
    user_repository: UserRepositoryDependency, company_repository: CompanyRepositoryDependency
) -> AuthPublicService:
    """Get the public auth service.

    Args:
        user_repository: Database repository for user objects.
        company_repository: Database repository for company objects.

    Returns:
        AuthPublicService: Public auth service.
    """
    return AuthPublicService(user_repository=user_repository, company_repository=company_repository)


AuthPublicServiceDependency = Annotated[AuthPublicService, Depends(get_public_auth_service)]
