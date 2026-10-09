from sqlalchemy import MetaData

from src.core.models.base import BaseModel


class AuthBaseModel(BaseModel):
    """Base database model for the auth module.

    Attributes:
        id: UUID
    """

    __abstract__ = True
    metadata = MetaData(schema="auth")
