from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from ..resources.enums import InvitePurposeEnum
from .mixins import IdMixin


class InviteToken(BaseModel):
    """Invite scheme.

    Attributes:
        invite_token: str
    """

    invite_token: str = Field(max_length=120)


class InviteTokenHashed(BaseModel):
    """Invite scheme.

    Attributes:
        token_hash: str
    """

    token_hash: str = Field(max_length=120)


class InviteCreation(InviteTokenHashed):
    """Invite creation scheme.

    Attributes:
        token_hash: str
        recipient_email: EmailStr
        expired_at: datetime
        purpose: InvitePurposeEnum
    """

    recipient_email: EmailStr = Field(max_length=120)
    expired_at: datetime
    purpose: InvitePurposeEnum


class InviteCreationResponse(IdMixin, InviteCreation):
    """Invite full scheme.

    Attributes:
        id: UUID
        token_hash: str
        recipient_email: EmailStr
        expired_at: datetime
        purpose: InvitePurposeEnum
        used_at: datetime | None
    """

    used_at: datetime | None
