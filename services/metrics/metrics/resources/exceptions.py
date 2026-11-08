from shared.resources.exceptions import DomainValidationError


class HeartbeatWorkerNotConfigured(DomainValidationError):
    """The service and worker role are not configured for monitoring."""

    _message: str = "Heartbeat worker is not configured."
