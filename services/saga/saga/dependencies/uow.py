from sqlalchemy.ext.asyncio import AsyncSession

from shared.uow.service import UowAbstract, UowSqlAlchemy


def get_uow(session: AsyncSession) -> UowAbstract:
    """Build a unit of work bound to an existing saga transaction."""
    return UowSqlAlchemy(session)
