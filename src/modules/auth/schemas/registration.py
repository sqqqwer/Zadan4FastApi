from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from .account import AccountEmail
from .company import CompanyName
from .invite import InviteToken
from .user import UserResponse, UserScheme


class PasswordScheme(BaseModel):
    """Scheme for password.

    Attributes:
        password(alias="pass"): SecretStr
    """

    password: SecretStr = Field(
        alias="pass",
        min_length=8,
        max_length=40,
    )


class CompanySignUpEmailConfirmation(AccountEmail, InviteToken):
    """Scheme for email confirmation during company registration.

    Attributes:
        email(alias="account"): EmailStr
        invite_token: str
    """


class UserRegistration(AccountEmail, UserScheme, PasswordScheme):
    """Scheme for user registration with a password.

    Attributes:
        email(alias="account"): EmailStr
        first_name: str | None
        last_name: str | None
        password(alias="pass"): SecretStr
    """


class UserEmployeeRegistration(AccountEmail, UserScheme):
    """Scheme for employee creation by an admin without a password.

    Attributes:
        email(alias="account"): EmailStr
        first_name: str | None
        last_name: str | None
    """


class UserEmployeeRegistrationResponse(UserResponse, InviteToken, AccountEmail):
    """Response scheme for employee creation by an admin.

    Attributes:
        id: UUID
        first_name: str | None
        last_name: str | None
        role: RoleEnum
        invite_token: str
        email(alias="account"): EmailStr
        invite_link: str
    """

    invite_link: str


class UserAdminAndCompanyRegistration(UserRegistration, CompanyName):
    """Scheme for creating an admin user and a company.

    Attributes:
        email(alias="account"): EmailStr
        first_name: str | None
        last_name: str | None
        password(alias="pass"): SecretStr
        company_name: str
    """


class UserAdminAndCompanyRegistrationResponse(UserScheme, CompanyName):
    """Response scheme for creating an admin user and a company.

    Attributes:
        first_name: str | None
        last_name: str | None
        company_name: str
        user_id: UUID
        company_id: UUID
    """

    user_id: UUID
    company_id: UUID
