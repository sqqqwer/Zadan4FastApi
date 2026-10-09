from typing import Annotated

from fastapi import Depends

from src.core.dependencies.session import SessionDependency

from ..repositories.abstracts import (
    AccountAbstractRepository,
    CompanyAbstractRepository,
    RefreshSessionAbstractRepository,
    UserAbstractRepository,
)
from ..repositories.sqlalchemy_repositories import (
    AccountSqlAlchemyRepository,
    CompanySqlAlchemyRepository,
    RefreshSessionSqlAlchemyRepository,
    UserSqlAlchemyRepository,
)


def get_account_repository(session: SessionDependency) -> AccountAbstractRepository:
    """Get the account repository.

    Args:
        session: Database session used by the repository.

    Returns:
        AccountAbstractRepository: Account repository.
    """
    return AccountSqlAlchemyRepository(session)


def get_company_repository(session: SessionDependency) -> CompanyAbstractRepository:
    """Get the company repository.

    Args:
        session: Database session used by the repository.

    Returns:
        CompanyAbstractRepository: Company repository.
    """
    return CompanySqlAlchemyRepository(session)


def get_user_repository(session: SessionDependency) -> UserAbstractRepository:
    """Get the user repository.

    Args:
        session: Database session used by the repository.

    Returns:
        UserAbstractRepository: User repository.
    """
    return UserSqlAlchemyRepository(session)


def get_refresh_session_repository(session: SessionDependency) -> RefreshSessionAbstractRepository:
    """Get the refresh session repository.

    Args:
        session: Database session used by the repository.

    Returns:
        RefreshSessionAbstractRepository: Refresh session repository.
    """
    return RefreshSessionSqlAlchemyRepository(session)


AccountRepositoryDependency = Annotated[AccountAbstractRepository, Depends(get_account_repository)]
CompanyRepositoryDependency = Annotated[CompanyAbstractRepository, Depends(get_company_repository)]
UserRepositoryDependency = Annotated[UserAbstractRepository, Depends(get_user_repository)]
RefreshSessionRepositoryDependency = Annotated[
    RefreshSessionAbstractRepository, Depends(get_refresh_session_repository)
]
