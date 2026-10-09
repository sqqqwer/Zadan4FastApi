from enum import StrEnum


class RoleEnum(StrEnum):
    """User roles in a company."""

    ADMIN = "admin"
    EMPLOYEE = "employee"
