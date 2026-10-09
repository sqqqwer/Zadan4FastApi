from pydantic import BaseModel, Field

from src.core.resources.enums import RoleEnum

from .mixins import IdMixin


class UserScheme(BaseModel):
    """User scheme.

    Attributes:
        first_name: str | None
        last_name: str | None
    """

    first_name: str | None = Field(max_length=120)
    last_name: str | None = Field(max_length=120)


class UserResponse(UserScheme, IdMixin):
    """User scheme response.

    Attributes:
        id: UUID
        first_name: str | None
        last_name: str | None
        role: RoleEnum
    """

    role: RoleEnum
