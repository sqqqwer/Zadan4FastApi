from uuid import UUID

from pydantic import BaseModel

from src.core.resources.enums import RoleEnum


class UserRef(BaseModel):
    """User data shared between modules."""

    id: UUID
    first_name: str | None
    last_name: str | None
    role: RoleEnum
    company_id: UUID


class CompanyRef(BaseModel):
    """Company data shared between modules."""

    id: UUID
    name: str
