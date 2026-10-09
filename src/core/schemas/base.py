from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseModelResponseScheme(BaseModel):
    """Base response schema with an object ID.

    Attributes:
        id: UUID
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID


class BaseModelCreateScheme(BaseModel):
    """Base schema for creating an object."""


class BaseModelUpdateScheme(BaseModel):
    """Base schema for updating an object."""
