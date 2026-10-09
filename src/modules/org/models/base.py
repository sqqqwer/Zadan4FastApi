from sqlalchemy import MetaData

from src.core.models.base import BaseModel


class OrgBaseModel(BaseModel):
    """Base database model for the org module.

    Attributes:
        id: UUID
    """

    __abstract__ = True
    metadata = MetaData(schema="org")
