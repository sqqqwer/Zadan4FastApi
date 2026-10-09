from typing import Annotated

from fastapi import Depends

from src.core.dependencies.session import SessionDependency
from src.core.services.uow import UowAbstract, UowSqlAlchemy


def get_uow(session: SessionDependency) -> UowAbstract:
    """Get the unit of work.

    Args:
        session: Database session used by the unit of work.

    Returns:
        UowAbstract: Unit of work.
    """
    return UowSqlAlchemy(session)


UowDependency = Annotated[UowAbstract, Depends(get_uow)]
