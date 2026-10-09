from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.core.resources.enums import RoleEnum


class AccessTokenClaims(BaseModel):
    """JWT access token claims.

    Attributes:
        sub: UUID
        company_id: UUID
        role: RoleEnum
        iss: str
        aud: str
        iat: datetime
        exp: datetime
        jti: UUID
    """

    sub: UUID
    company_id: UUID
    role: RoleEnum

    iss: str
    aud: str
    iat: datetime
    exp: datetime
    jti: UUID
