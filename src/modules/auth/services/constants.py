from datetime import timedelta

EMPLOYEE_INVITE_FRONT_PATH = "employee-invite"
EMAIL_CHANGE_FRONT_PATH = "email-change"

EVENT_PRODUCER = "auth"


REGISTRATION_SESSION_ALIAS = "registration_session"
REGISTRATION_SESSION_EXPIRED_TTL = timedelta(minutes=15)

INVITE_EXPIRED_TTL_ON_CHECK_EMAIL = timedelta(hours=12)
INVITE_EXPIRED_TTL_ON_EMPLOYEE_CREATE = timedelta(days=1)
INVITE_EXPIRED_TTL_ON_CHANGE_EMAIL = timedelta(hours=3)

ACCESS_TOKEN_EXPIRED_TTL = timedelta(hours=3)
REFRESH_TOKEN_EXPIRED_TTL = timedelta(days=2)
