from pydantic import BaseModel, EmailStr, Field

from .mixins import IdMixin


class AccountEmail(BaseModel):
    """Account scheme.

    Attributes:
        email(alias="account"): EmailStr
    """

    email: EmailStr = Field(alias="account", max_length=120)


class AccountEmailResponse(AccountEmail, IdMixin):
    """Account scheme response.

    Attributes:
        id: UUID
        email(alias="account"): EmailStr
    """
