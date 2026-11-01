from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .account import Account


class RegistrationSession(AuthBaseModel):
    """Database model for a one-time registration session.

    Attributes:
        id: UUID
        token_hash: str
        expires_at: datetime
        account_id: UUID
        account: Account
    """

    __tablename__ = "registration_session"

    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id", ondelete="CASCADE"), index=True)

    account: Mapped["Account"] = relationship(back_populates="registration_sessions")
