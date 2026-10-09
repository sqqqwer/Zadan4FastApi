from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuthBaseModel

if TYPE_CHECKING:
    from .members import Members


class Company(AuthBaseModel):
    """Database model for a company.

    Attributes:
        id: UUID
        name: str
        members: list[Members]
    """

    __tablename__ = "company"

    name: Mapped[str] = mapped_column(unique=True)
    members: Mapped[list["Members"]] = relationship(
        back_populates="company", cascade="all, delete", passive_deletes=True
    )
