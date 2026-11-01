from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import OrgBaseModel
from .types import LtreeType

if TYPE_CHECKING:
    from .struct_adm_positions import StructAdmPositions


class StructAdm(OrgBaseModel):
    """Database model for a company struct.

    Attributes:
        id: UUID
        name: str
        path: str
        company_id: UUID
        director_user_id: UUID | None
        struct_adm_positions: list[StructAdmPositions]
    """

    __tablename__ = "struct_adm"

    name: Mapped[str]

    path: Mapped[str] = mapped_column(LtreeType())

    company_id: Mapped[UUID]
    director_user_id: Mapped[UUID | None]

    struct_adm_positions: Mapped[list["StructAdmPositions"]] = relationship(
        back_populates="struct_adm", passive_deletes="all"
    )

    __table_args__ = (
        Index("index_struct_adm_path_gist", "path", postgresql_using="gist"),
        UniqueConstraint("company_id", "path", name="unique_pair_company_id_path"),
    )
