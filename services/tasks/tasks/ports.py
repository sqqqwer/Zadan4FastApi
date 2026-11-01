from typing import Protocol
from uuid import UUID

from .public.dto import UserRef


class UserDirectory(Protocol):
    """Interface for getting user data."""

    async def get_many(self, user_ids: list[UUID]) -> dict[UUID, UserRef]:
        """Get users by their IDs.

        Args:
            user_ids: User IDs.

        Returns:
            dict[UUID, UserRef]: Found users indexed by their IDs.
        """
        ...
