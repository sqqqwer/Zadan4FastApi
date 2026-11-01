from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .invite import Invite
    from .registration_session import RegistrationSession
    from .secrets import Secrets


class Account(AuthBaseModel):
    """Database model for a user account.

    Attributes:
        id: UUID
        email: str
        secrets: Secrets | None
        invites: list[Invite]
        registration_sessions: list[RegistrationSession]
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
    registration_sessions: Mapped[list["RegistrationSession"]] = relationship(
        back_populates="account",
        cascade="all, delete",
        passive_deletes=True,
    )
