from uuid import UUID

from pydantic import BaseModel, Field

from src.core.schemas.base import BaseModelCreateScheme, BaseModelResponseScheme, BaseModelUpdateScheme


class PositionNameScheme(BaseModel):
    """Position name schema.

    Attributes:
        name: str
    """

    name: str = Field(max_length=120)


class PositionCreateScheme(BaseModelCreateScheme, BaseModelUpdateScheme, PositionNameScheme):
    """Data for creating or updating a position.

    Attributes:
        name: str
    """


class PositionAssignUserScheme(BaseModel):
    """User ID for assignment to a position.

    Attributes:
        user_id: UUID
    """

    user_id: UUID


class PositionResponseScheme(BaseModelResponseScheme, PositionNameScheme):
    """Position response schema.

    Attributes:
        id: UUID
        name: str
        company_id: UUID
    """

    company_id: UUID


class PositionListResponseScheme(PositionResponseScheme):
    """Position response schema with a user count.

    Attributes:
        id: UUID
        name: str
        company_id: UUID
        users_count: int | None
    """

    users_count: int | None
