from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .invite import Invite
    from .secrets import Secrets


class Account(AuthBaseModel):
    """Database model for a user account.

    Attributes:
        id: UUID
        email: str
        secrets: Secrets | None
        invites: list[Invite]
    """

    __tablename__ = "account"

    email: Mapped[str] = mapped_column(unique=True)

    secrets: Mapped["Secrets | None"] = relationship(
        back_populates="account",
        cascade="all, delete",
        passive_deletes=True,
    )
    invites: Mapped[list["Invite"]] = relationship(
        back_populates="account", cascade="all, delete", passive_deletes=True
    )
