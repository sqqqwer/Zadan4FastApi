from sqlalchemy import MetaData

from src.core.models.base import BaseModel, BaseModelWithoutId


class AuthBaseModelWithoutId(BaseModelWithoutId):
    """Base database model for the auth schema without a predefined primary key."""

    __abstract__ = True
    metadata = MetaData(schema="auth")


class AuthBaseModel(AuthBaseModelWithoutId, BaseModel):
    """Base database model for the auth module.

    Attributes:
        id: UUID
    """

    __abstract__ = True
