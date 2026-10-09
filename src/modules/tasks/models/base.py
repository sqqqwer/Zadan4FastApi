from sqlalchemy import MetaData

from src.core.models.base import BaseModel


class TasksBaseModel(BaseModel):
    """Base database model for the tasks module.

    Attributes:
        id: UUID
    """

    __abstract__ = True
    metadata = MetaData(schema="tasks")
