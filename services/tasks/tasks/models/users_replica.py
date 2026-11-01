from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TasksBaseModelWithoutId


class UsersReplicaTasks(TasksBaseModelWithoutId):
    """Minimal local user data received from auth events.

    Attributes:
        id: User ID assigned by auth, never generated locally.
        full_name: User display name.
        company_id: Company ID assigned by auth.
        is_active: User activity state supplied by auth.
        updated_at: Time of the local replica update.
        last_event_at: Occurrence time of the last applied auth event.
    """

    __tablename__ = "users_replica"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    full_name: Mapped[str]
    company_id: Mapped[UUID]
    is_active: Mapped[bool]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
