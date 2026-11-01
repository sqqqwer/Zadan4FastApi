from sqlalchemy.orm import DeclarativeBase

from .mixins import IdPrimaryKeyMixin


class BaseModelWithoutId(DeclarativeBase):
    """Base database model without a predefined primary key."""

    __abstract__ = True


class BaseModel(IdPrimaryKeyMixin, BaseModelWithoutId):
    """Base database model.

    Attributes:
        id: UUID
    """

    __abstract__ = True
