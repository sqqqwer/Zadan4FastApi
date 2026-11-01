from typing import Annotated

from fastapi import Depends

from shared.uow.service import UowAbstract, UowSqlAlchemy

from .session import SessionDependency


def get_uow(session: SessionDependency) -> UowAbstract:
    """Build a unit of work using the request's database session."""
    return UowSqlAlchemy(session)


UowDependency = Annotated[UowAbstract, Depends(get_uow)]
