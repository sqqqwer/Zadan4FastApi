from datetime import datetime

from pydantic import BaseModel, Field

from .mixins import IdMixin


class RefreshSessionTokenHash(BaseModel):
    """Refresh token hash used to find a session.

    Attributes:
        token_hash: str
    """

    token_hash: str = Field(max_length=120)


class RefreshSessionUpdate(BaseModel):
    """Data for updating refresh session dates.

    Attributes:
        created_at: datetime
        expires_at: datetime
        revoked_at: datetime | None
    """

    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class RefreshSessionCreation(RefreshSessionTokenHash, RefreshSessionUpdate):
    """Data for creating a refresh session.

    Attributes:
        token_hash: str
        created_at: datetime
        expires_at: datetime
        revoked_at: datetime | None
    """


class RefreshSessionCreationResponse(IdMixin, RefreshSessionCreation):
    """Response schema for a created refresh session.

    Attributes:
        id: UUID
        token_hash: str
        created_at: datetime
        expires_at: datetime
        revoked_at: datetime | None
    """
