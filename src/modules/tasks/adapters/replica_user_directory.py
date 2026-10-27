from uuid import UUID

from ..public.dto import UserRef
from ..repositories.abstracts import ReplicaUserAbstractRepository


class TasksReplicaUserDirectory:
    """User directory backed by the tasks module's local replica."""

    def __init__(self, repository: ReplicaUserAbstractRepository) -> None:
        """Initialize the directory.

        Args:
            repository: Repository for the module's user replicas.
        """
        self.repository = repository

    async def get_many(self, user_ids: list[UUID]) -> dict[UUID, UserRef]:
        """Get replicated users by their IDs in one query.

        Args:
            user_ids: User IDs to look up.

        Returns:
            dict[UUID, UserRef]: Found users indexed by their IDs.
        """
        users = await self.repository.get_many(user_ids)
        return {
            user.id: UserRef(
                user_id=user.id,
                full_name=user.full_name,
                company_id=user.company_id,
            )
            for user in users
        }
