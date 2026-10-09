from uuid import UUID

from pydantic import BaseModel


class UserRef(BaseModel):
    """User data shared between modules."""

    user_id: UUID
    company_id: UUID
