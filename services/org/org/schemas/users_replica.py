from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReplicaUserCreateScheme(BaseModel):
    """User data received from auth for the local replica."""

    id: UUID
    full_name: str
    company_id: UUID
    is_active: bool
    last_event_at: datetime
