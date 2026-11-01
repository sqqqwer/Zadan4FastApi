from enum import StrEnum


class InvitePurposeEnum(StrEnum):
    """Supported invite purposes."""

    COMPANY_REGISTRATION = "company_registration"
    EMPLOYEE_INVITATION = "employee_invitation"
    EMAIL_CHANGE = "email_change"
