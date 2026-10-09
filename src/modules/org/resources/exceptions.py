from src.core.resources.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
)


class OrgModuleError(AppError):
    """Base error for the org module."""

    _message: str = "Org Module Error."


class StructNotFound(OrgModuleError, NotFoundError):
    """The struct is not found."""

    _message: str = "Struct not found."


class PositionNotFound(OrgModuleError, NotFoundError):
    """The position is not found."""

    _message: str = "Position not found."


class PositionAlreadyInStruct(OrgModuleError, ConflictError):
    """The position is already assigned to a struct."""

    _message: str = "Position already in struct."


class StructPositionNotFound(OrgModuleError, NotFoundError):
    """The position assignment to the struct is not found."""

    _message: str = "Struct-Position relationship not found."


class StructSubtreeHasPositions(OrgModuleError, ConflictError):
    """The struct or its subtree has assigned positions."""

    _message: str = "Structs in subtree have Positions."


class StructMoveToHimself(OrgModuleError, ConflictError):
    """The struct cannot be moved into itself."""

    _message: str = "Struct move to himself."


class StructMoveTargetInSubTree(OrgModuleError, ConflictError):
    """The target struct is in the subtree being moved."""

    _message: str = "Struct move target in subtree."


class UserNotFound(OrgModuleError, NotFoundError):
    """The user is not found."""

    _message: str = "User not found."


class UserNotInCompany(OrgModuleError, ConflictError):
    """The user belongs to a different company."""

    _message: str = "User in wrong company."


class UserWithPositionNotFound(OrgModuleError, NotFoundError):
    """The user assignment to the position is not found."""

    _message: str = "User with Position not found."
