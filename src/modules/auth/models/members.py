from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.resources.enums import RoleEnum

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .company import Company
    from .user import User


class Members(AuthBaseModel):
    """Database model for a user membership in a company.

    Attributes:
        id: UUID
        role: RoleEnum
        company_id: UUID
        user_id: UUID
        company: Company
        user: User
    """

    __tablename__ = "members"

    role: Mapped[RoleEnum] = mapped_column(
        SAEnum(
            RoleEnum,
            name="members_role",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        )
    )

    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True)

    company: Mapped["Company"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="membership")
