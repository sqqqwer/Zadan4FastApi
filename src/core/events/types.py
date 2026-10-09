from enum import StrEnum


class EventType(StrEnum):
    """Supported event types."""

    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_REGISTERED = "employee.registered"
    EMPLOYEE_EMAIL_CHANGED = "employee.email_changed"
    TASK_STATUS_CHANGED = "task.status_changed"
