from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.auth.public.service import AuthPublicService
from src.modules.tasks.public.dto import UserRef as TasksUserRef

if TYPE_CHECKING:
    from src.modules.auth.public.dto import UserRef as AuthUserRef


class TasksLocalUserDirectory:
    """User directory for the tasks module using the auth service."""

    def __init__(self, auth_service: AuthPublicService):
        """Initialize the user directory.

        Args:
            auth_service: Public auth service used to get user data.
        """
        self._auth_service = auth_service

    async def get_many(self, user_ids: list[UUID]) -> dict[UUID, TasksUserRef]:
        """Get users by their IDs.

        Args:
            user_ids: User IDs.

        Returns:
            dict[UUID, TasksUserRef]: Users with company membership, indexed by their IDs.
        """
        users: dict[UUID, AuthUserRef] = await self._auth_service.get_many_users(user_ids)
        return {
            user.id: TasksUserRef(
                user_id=user.id,
                full_name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
                company_id=user.company_id,
            )
            for user in users.values()
        }
