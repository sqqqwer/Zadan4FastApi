from typing import Literal

from pydantic import BaseModel, SecretStr

from .account import AccountEmail
from .registration import PasswordScheme


class LoginScheme(AccountEmail, PasswordScheme):
    """Scheme for login.

    Attributes:
        email(alias="account"): EmailStr
        password(alias="pass"): SecretStr
    """


class RefreshToken(BaseModel):
    """Request schema containing a refresh token.

    Attributes:
        refresh_token: SecretStr
    """

    refresh_token: SecretStr


class RefreshTokenResponse(BaseModel):
    """Response schema containing a refresh token.

    Attributes:
        refresh_token: str
    """

    refresh_token: str


class TokenResponse(RefreshTokenResponse):
    """Response schema with access and refresh tokens.

    Attributes:
        refresh_token: str
        access_token: str
        token_type: Literal['bearer']
        expires_in: int
    """

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
