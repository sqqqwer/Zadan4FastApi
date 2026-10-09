from uuid import UUID

from pydantic import BaseModel, Field

from src.core.schemas.base import BaseModelCreateScheme, BaseModelResponseScheme, BaseModelUpdateScheme


class StructNameScheme(BaseModel):
    """Struct name schema.

    Attributes:
        name: str
    """

    name: str = Field(max_length=120)


class StructPathScheme(BaseModel):
    """Struct path schema.

    Attributes:
        path: str
    """

    path: str


class StructCreateScheme(BaseModelCreateScheme, BaseModelUpdateScheme, StructNameScheme):
    """Data for creating or updating a struct.

    Attributes:
        name: str
    """


class StructResponseScheme(BaseModelResponseScheme, StructPathScheme, StructNameScheme):
    """Struct response schema.

    Attributes:
        id: UUID
        path: str
        name: str
        company_id: UUID
        director_user_id: UUID | None
    """

    company_id: UUID
    director_user_id: UUID | None


class StructTreeResponseChildStructScheme(StructNameScheme, StructPathScheme):
    """Name and path of a child struct.

    Attributes:
        name: str
        path: str
    """


class StructTreeResponseScheme(StructResponseScheme):
    """Struct response schema with child paths.

    Attributes:
        id: UUID
        path: str
        name: str
        company_id: UUID
        director_user_id: UUID | None
        child_paths: list[StructTreeResponseChildStructScheme]
    """

    child_paths: list[StructTreeResponseChildStructScheme]


class StructMoveToScheme(BaseModel):
    """Target struct ID for moving a struct.

    Attributes:
        struct_id: UUID | None
    """

    struct_id: UUID | None


class StructAssignPositionScheme(BaseModel):
    """Position ID for assignment to a struct.

    Attributes:
        position_id: UUID
    """

    position_id: UUID


class StructAssignDirectorScheme(BaseModel):
    """User ID for assignment as a struct director.

    Attributes:
        director_user_id: UUID
    """

    director_user_id: UUID
