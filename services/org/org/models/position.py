from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Mapped, query_expression, relationship

from .base import OrgBaseModel

if TYPE_CHECKING:
    from .struct_adm_positions import StructAdmPositions
    from .users_positions import UsersPositions


class Position(OrgBaseModel):
    """Database model for a company position.

    Attributes:
        id: UUID
        name: str
        company_id: UUID
        users_position: list[UsersPositions]
        struct_adm_positions: StructAdmPositions | None
        users_count: int | None - query_expression()
    """

    __tablename__ = "position"

    name: Mapped[str]
    company_id: Mapped[UUID]

    users_position: Mapped[list["UsersPositions"]] = relationship(back_populates="position", passive_deletes="all")
    struct_adm_positions: Mapped["StructAdmPositions | None"] = relationship(
        back_populates="position", passive_deletes="all"
    )

    users_count: Mapped[int | None] = query_expression()
