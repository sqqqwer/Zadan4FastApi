from shared.base.models.models import BaseModel, BaseModelWithoutId
from sqlalchemy import MetaData


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
