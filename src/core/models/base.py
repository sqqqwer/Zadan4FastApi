from sqlalchemy.orm import DeclarativeBase

from .mixins import IdPrimaryKeyMixin


class BaseModel(IdPrimaryKeyMixin, DeclarativeBase):
    """Base database model.

    Attributes:
        id: UUID
    """

    __abstract__ = True
