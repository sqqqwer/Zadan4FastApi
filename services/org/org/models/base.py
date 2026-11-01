from shared.base.models.models import BaseModel, BaseModelWithoutId
from sqlalchemy import MetaData


class OrgBaseModelWithoutId(BaseModelWithoutId):
    """Base database model for the org schema without a predefined primary key."""

    __abstract__ = True
    metadata = MetaData(schema="org")


class OrgBaseModel(OrgBaseModelWithoutId, BaseModel):
    """Base database model for the org module.

    Attributes:
        id: UUID
    """

    __abstract__ = True
