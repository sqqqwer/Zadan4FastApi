from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import OrgBaseModel

if TYPE_CHECKING:
    from .position import Position


class UsersPositions(OrgBaseModel):
    """Database model linking a user and a position.

    Attributes:
        id: UUID
        user_id: UUID
        position_id: UUID
        position: Position
    """

    __tablename__ = "users_positions"

    user_id: Mapped[UUID]
    position_id: Mapped[UUID] = mapped_column(ForeignKey("position.id", ondelete="CASCADE"))

    position: Mapped["Position"] = relationship(back_populates="users_position")

    __table_args__ = (UniqueConstraint("user_id", "position_id", name="unique_pair_user_id_position_id"),)
