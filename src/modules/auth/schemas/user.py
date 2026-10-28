from uuid import UUID

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


class UserLookupPayload(BaseModel):
    """User IDs requested by a directory fallback.

    Attributes:
        user_ids: IDs of users missing from the local replica.
    """

    user_ids: list[UUID] = Field(min_length=1)


class UserLookupResponse(BaseModel):
    """Minimal user data returned to other services.

    Attributes:
        user_id: User ID.
        full_name: User display name.
        company_id: Company the user belongs to.
        is_active: Whether the user is active.
    """

    user_id: UUID
    full_name: str
    company_id: UUID
    is_active: bool
