from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import OrgBaseModel

if TYPE_CHECKING:
    from .position import Position
    from .struct_adm import StructAdm


class StructAdmPositions(OrgBaseModel):
    """Database model linking a struct and a position.

    Attributes:
        id: UUID
        struct_adm_id: UUID
        position_id: UUID
        struct_adm: StructAdm
        position: Position
    """

    __tablename__ = "struct_adm_positions"

    struct_adm_id: Mapped[UUID] = mapped_column(ForeignKey("struct_adm.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("position.id", ondelete="CASCADE"), unique=True)

    struct_adm: Mapped["StructAdm"] = relationship(back_populates="struct_adm_positions")
    position: Mapped["Position"] = relationship(back_populates="struct_adm_positions")
