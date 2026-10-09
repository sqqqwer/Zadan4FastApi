class AppError(Exception):
    """Base application error."""

    _message: str = "App error."

    def __str__(self):
        return self._message


class NotFoundError(AppError):
    """The requested object is not found."""

    _message: str = "Entity Not Found."


class ConflictError(AppError):
    """The operation conflicts with existing data."""

    _message: str = "Entity Conflict."


class DomainValidationError(AppError):
    """The data does not satisfy domain rules."""

    _message: str = "Validation Error."


class AuthenticationError(AppError):
    """Authentication fails."""

    _message: str = "Authentication Error."


class AuthorizationError(AppError):
    """The user does not have permission for the operation."""

    _message: str = "Authorization Error."


class IdempotencyDifferentRequestError(ConflictError):
    """The idempotency key was already used with different request data."""

    _message: str = "This idempotency key has already been used with different request data."
