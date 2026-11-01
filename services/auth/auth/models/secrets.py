from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .account import Account
    from .user import User


class Secrets(AuthBaseModel):
    """Database model linking a user, an account, and a password hash.

    Attributes:
        id: UUID
        password_hash: str | None
        user_id: UUID
        account_id: UUID
        user: User
        account: Account
    """

    __tablename__ = "secrets"

    password_hash: Mapped[str | None]

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id", ondelete="CASCADE"), unique=True)

    user: Mapped["User"] = relationship(back_populates="secrets")

    account: Mapped["Account"] = relationship(back_populates="secrets")
