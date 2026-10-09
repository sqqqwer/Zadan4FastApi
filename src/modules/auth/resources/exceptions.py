from src.core.resources.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
)


class AuthModuleError(AppError):
    """Base error for the auth module."""

    _message: str = "Auth Module Error."


class AccountWithEmailAlreadyExists(AuthModuleError, ConflictError):
    """An account with this email already exists."""

    _message: str = "Account with this email already exists."


class AccountNotFound(AuthModuleError, NotFoundError):
    """The account is not found."""

    _message: str = "Account not found."


class InviteNotFound(AuthModuleError, NotFoundError):
    """The invite is not found."""

    _message: str = "Invite not found."


class InviteExpired(AuthModuleError, DomainValidationError):
    """The invite has expired."""

    _message: str = "Invite has expired."


class InviteWrongPurpose(AuthModuleError, DomainValidationError):
    """The invite has a different purpose."""

    _message: str = "Invite has wrong registration purpose."


class InviteAlreadyUsed(AuthModuleError, ConflictError):
    """The invite has already been used."""

    _message: str = "Invite already used."


class InviteNotMatchingEmailWithAccount(AuthModuleError, DomainValidationError):
    """The invite does not match the email or account."""

    _message: str = "Invite created for different email."


class CompanyWithThisNameAlreadyExists(AuthModuleError, ConflictError):
    """A company with this name already exists."""

    _message: str = "Company with this name already exists."


class CompanyNotFound(AuthModuleError, NotFoundError):
    """The company is not found."""

    _message: str = "Company not found."


class UserWithThisAccountAlreadyExists(AuthModuleError, ConflictError):
    """A user is already linked to this account."""

    _message: str = "User with this email already exists."


class UserNotHaveMembership(AuthModuleError, NotFoundError):
    """The user does not have a company membership."""

    _message: str = "User does not have membership."


class UserNotFound(AuthModuleError, NotFoundError):
    """The user is not found."""

    _message: str = "User not found."


class SecretsPasswordAlreadyExists(AuthModuleError, ConflictError):
    """The account already has a password."""

    _message: str = "Secrets password already exists."


class SecretsNotExists(AuthModuleError, ConflictError):
    """The account secrets are not found."""

    _message: str = "Secrets not Exists."


class NewEmailMatchesCurrentEmail(AuthModuleError, ConflictError):
    """The new email matches the current email."""

    _message = "New email must be different from current email."


class InvalidCredentials(AuthModuleError, AuthenticationError):
    """The authentication data is invalid."""

    _message = "Invalid authentication data."
