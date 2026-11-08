from collections.abc import Mapping
from typing import override

from httpx import URL, AsyncClient, HTTPError

from .abstracts import HeartbeatAbstractSender
from .exceptions import HeartbeatDeliveryError


class HttpHeartbeatSender(HeartbeatAbstractSender):
    """Send progress timestamps using an injected HTTP client and endpoint."""

    def __init__(self, client: AsyncClient, endpoint: str, attributes: Mapping[str, str]) -> None:
        """Configure the destination and application-supplied payload attributes."""
        url = URL(endpoint)
        if not url.is_absolute_url or url.scheme not in {"http", "https"}:
            raise ValueError("Heartbeat endpoint must be an absolute HTTP or HTTPS URL")
        if "last_progress_timestamp" in attributes:
            raise ValueError("Heartbeat attributes must not override the progress timestamp")
        self.client = client
        self.endpoint = url
        self.attributes = dict(attributes)

    @override
    async def send(self, last_progress_timestamp: float) -> None:
        try:
            response = await self.client.post(
                self.endpoint,
                json={**self.attributes, "last_progress_timestamp": last_progress_timestamp},
                follow_redirects=False,
            )
            response.raise_for_status()
        except HTTPError as error:
            raise HeartbeatDeliveryError(str(error)) from error
