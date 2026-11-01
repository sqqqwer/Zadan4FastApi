from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..resources.enums import InvitePurposeEnum
from .base import AuthBaseModel

if TYPE_CHECKING:
    from .account import Account


class Invite(AuthBaseModel):
    """Database model for an invite.

    Attributes:
        id: UUID
        token_hash: str
        expired_at: datetime
        used_at: datetime | None
        purpose: InvitePurposeEnum
        recipient_email: str
        account_id: UUID | None
        account: Account | None
    """

    __tablename__ = "invite"

    token_hash: Mapped[str] = mapped_column(unique=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purpose: Mapped[InvitePurposeEnum] = mapped_column(
        SAEnum(
            InvitePurposeEnum,
            name="invite_purpose",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        )
    )
    recipient_email: Mapped[str]

    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"),
    )

    account: Mapped["Account | None"] = relationship(back_populates="invites")
