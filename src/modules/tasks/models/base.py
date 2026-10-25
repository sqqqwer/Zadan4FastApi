from sqlalchemy import MetaData

from src.core.models.base import BaseModel, BaseModelWithoutId


class TasksBaseModelWithoutId(BaseModelWithoutId):
    """Base database model for the tasks schema without a predefined primary key."""

    __abstract__ = True
    metadata = MetaData(schema="tasks")


class TasksBaseModel(TasksBaseModelWithoutId, BaseModel):
    """Base database model for the tasks module.

    Attributes:
        id: UUID
    """

    __abstract__ = True
