from uuid import UUID

from ..ports import UserDirectory
from ..public.dto import UserRef
from ..repositories.abstracts import ReplicaUserAbstractRepository


class OrgReplicaUserDirectory:
    """User directory backed by the org module's local replica."""

    def __init__(self, repository: ReplicaUserAbstractRepository, fallback: UserDirectory) -> None:
        """Initialize the directory.

        Args:
            repository: Repository for the module's user replicas.
            fallback: HTTP user directory used for a missing user.
        """
        self.repository = repository
        self.fallback = fallback

    async def get_user(self, user_id: UUID) -> UserRef | None:
        """Get a user from the replica or the HTTP fallback.

        Args:
            user_id: User ID to look up.

        Returns:
            UserRef: User data from the replica or auth.
            None: If neither source returns the user.

        Raises:
            AuthenticationError: If auth rejects the access token.
            AuthorizationError: If auth denies access.
            AuthUnavailableError: If the HTTP fallback cannot verify the user.
        """
        user = await self.repository.get_user(user_id)
        if user is None:
            return await self.fallback.get_user(user_id)

        return UserRef(user_id=user.id, company_id=user.company_id)
