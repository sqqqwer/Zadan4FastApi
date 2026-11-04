from enum import StrEnum


class EventType(StrEnum):
    """Supported event types."""

    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_REGISTERED = "employee.registered"
    EMPLOYEE_EMAIL_CHANGED = "employee.email_changed"
    TASK_STATUS_CHANGED = "task.status_changed"

    ORG_ASSIGN_EMPLOYEE = "org.assign_employee"
    ORG_EMPLOYEE_ASSIGNED = "org.employee_assigned"
    ORG_EMPLOYEE_ASSIGNMENT_FAILED = "org.employee_assignment_failed"
    ORG_UNASSIGN_EMPLOYEE = "org.unassign_employee"
    ORG_EMPLOYEE_UNASSIGNED = "org.employee_unassigned"

    TASKS_CREATE_WELCOME_TASK = "tasks.create_welcome_task"
    TASKS_WELCOME_TASK_CREATED = "tasks.welcome_task_created"
    TASKS_WELCOME_TASK_CREATION_FAILED = "tasks.welcome_task_creation_failed"
    TASKS_CANCEL_WELCOME_TASK = "tasks.cancel_welcome_task"
    TASKS_WELCOME_TASK_CANCELLED = "tasks.welcome_task_cancelled"

    AUTH_INVALIDATE_INVITE = "auth.invalidate_invite"
    AUTH_INVITE_INVALIDATED = "auth.invite_invalidated"
