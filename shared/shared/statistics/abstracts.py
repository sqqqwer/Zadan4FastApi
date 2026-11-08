from abc import ABC, abstractmethod


class ProgressAbstractReporter(ABC):
    """Observer notified when a worker makes progress."""

    @abstractmethod
    def mark_progress(self) -> None:
        """Record actual progress in the worker loop."""
        ...


class HeartbeatAbstractSender(ABC):
    """Transport used to report the last worker progress timestamp."""

    @abstractmethod
    async def send(self, last_progress_timestamp: float) -> None:
        """Deliver a progress timestamp or raise HeartbeatDeliveryError."""
        ...
