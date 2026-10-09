from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .members import Members
    from .refresh_session import RefreshSession
    from .secrets import Secrets


class User(AuthBaseModel):
    """Database model for a user.

    Attributes:
        id: UUID
        first_name: str | None
        last_name: str | None
        secrets: Secrets | None
        membership: Members
        refresh_sessions: list[RefreshSession]
    """

    __tablename__ = "user"

    first_name: Mapped[str | None]
    last_name: Mapped[str | None]

    secrets: Mapped["Secrets | None"] = relationship(
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )
    membership: Mapped["Members"] = relationship(
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )
