from typing import Protocol
from uuid import UUID

from .public.dto import UserRef


class UserDirectory(Protocol):
    """Interface for getting user data."""

    async def get_user(self, user_id: UUID) -> UserRef | None:
        """Get the user.

        Args:
            user_id: User ID.

        Returns:
            UserRef: User data.
            None: If the object is not found.
        """
        ...
