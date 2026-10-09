from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .user import User


class RefreshSession(AuthBaseModel):
    """Database model for a refresh token session.

    Attributes:
        id: UUID
        token_hash: str
        created_at: datetime
        expires_at: datetime
        revoked_at: datetime | None
        user_id: UUID
        user: User
    """

    __tablename__ = "refresh_session"

    token_hash: Mapped[str] = mapped_column(
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
    )

    user: Mapped["User"] = relationship(back_populates="refresh_sessions")
