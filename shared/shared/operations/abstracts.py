from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any


class OperationsAbstractRepository(ABC):
    """Database operations needed for readiness and outbox diagnostics."""

    @abstractmethod
    async def check_connection(self) -> None:
        """Check that the database accepts queries."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Clear a failed readiness transaction."""
        ...

    @abstractmethod
    async def count_pending_outbox(self) -> int:
        """Count messages awaiting publication."""
        ...

    @abstractmethod
    async def list_pending_outbox(self, limit: int, offset: int) -> Sequence[Mapping[str, Any]]:
        """Get a page of publication diagnostics."""
        ...
