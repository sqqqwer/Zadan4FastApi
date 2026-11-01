from uuid import UUID

from ..ports import UserDirectory
from ..public.dto import UserRef
from ..repositories.abstracts import ReplicaUserAbstractRepository


class TasksReplicaUserDirectory:
    """User directory backed by the tasks module's local replica."""

    def __init__(self, repository: ReplicaUserAbstractRepository, fallback: UserDirectory) -> None:
        """Initialize the directory.

        Args:
            repository: Repository for the module's user replicas.
            fallback: HTTP user directory used for missing users.
        """
        self.repository = repository
        self.fallback = fallback

    async def get_many(self, user_ids: list[UUID]) -> dict[UUID, UserRef]:
        """Get users from the replica and request missing IDs through HTTP.

        Args:
            user_ids: User IDs to look up.

        Returns:
            dict[UUID, UserRef]: Found users indexed by their IDs.

        Raises:
            AuthenticationError: If auth rejects the access token.
            AuthorizationError: If auth denies access.
            AuthUnavailableError: If the HTTP fallback cannot verify the users.
        """
        users = await self.repository.get_many(user_ids)
        result = {
            user.id: UserRef(
                user_id=user.id,
                full_name=user.full_name,
                company_id=user.company_id,
            )
            for user in users
        }
        missing_ids = list(set(user_ids) - result.keys())
        if missing_ids:
            result.update(await self.fallback.get_many(missing_ids))
        return result
