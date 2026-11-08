from typing import Literal

from httpx import AsyncClient

from shared.statistics.heartbeat import HeartbeatReporter
from shared.statistics.http import HttpHeartbeatSender

from ..config import get_settings


def get_heartbeat_reporter(client: AsyncClient, role: Literal["consumer", "publisher"]) -> HeartbeatReporter:
    """Build a heartbeat reporter for one org worker."""
    settings = get_settings()
    sender = HttpHeartbeatSender(
        client=client,
        endpoint=settings.statistics_endpoint,
        attributes={"service": "org", "role": role},
    )
    return HeartbeatReporter(
        sender=sender,
        interval_seconds=settings.heartbeat_interval_seconds,
        timeout_seconds=settings.heartbeat_timeout_seconds,
    )
