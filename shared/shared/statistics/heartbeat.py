import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from math import isfinite
from time import monotonic, time
from typing import override

from .abstracts import HeartbeatAbstractSender, ProgressAbstractReporter
from .exceptions import HeartbeatDeliveryError

logger = logging.getLogger(__name__)


class HeartbeatReporter(ProgressAbstractReporter):
    """Track worker progress and deliver heartbeats at a limited rate."""

    def __init__(
        self,
        sender: HeartbeatAbstractSender,
        interval_seconds: float = 5.0,
        timeout_seconds: float = 1.0,
    ) -> None:
        """Configure the transport, attempt interval and delivery timeout."""
        if any(not isfinite(value) or value <= 0 for value in (interval_seconds, timeout_seconds)):
            raise ValueError("Heartbeat interval and timeout must be positive finite values")
        self.sender = sender
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.last_progress_timestamp: float | None = None
        self._last_attempt_monotonic: float | None = None
        self._send_lock = asyncio.Lock()

    @override
    def mark_progress(self) -> None:
        """Record actual worker progress independently of heartbeat delivery."""
        self.last_progress_timestamp = time()

    async def send_if_due(self) -> bool:
        """Deliver the stored timestamp when due without interrupting the worker."""
        timestamp = self.last_progress_timestamp
        if timestamp is None or self._send_lock.locked():
            return False
        async with self._send_lock:
            now = monotonic()
            if self._last_attempt_monotonic is not None and now - self._last_attempt_monotonic < self.interval_seconds:
                return False
            self._last_attempt_monotonic = now
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    await self.sender.send(timestamp)
            except (HeartbeatDeliveryError, TimeoutError) as error:
                logger.warning("Heartbeat delivery failed: error=%s", error)
                return False
        return True

    @asynccontextmanager
    async def running(self) -> AsyncGenerator[None]:
        """Run delivery in the background and stop it when the worker exits."""
        async with asyncio.TaskGroup() as group:
            task = group.create_task(self._send_loop())
            try:
                yield
            finally:
                task.cancel()

    async def _send_loop(self) -> None:
        """Periodically deliver stored progress without updating its timestamp."""
        while True:
            await self.send_if_due()
            await asyncio.sleep(self.interval_seconds)
