from uuid import UUID

from ..public.dto import UserRef
from ..repositories.abstracts import ReplicaUserAbstractRepository


class OrgReplicaUserDirectory:
    """User directory backed by the org module's local replica."""

    def __init__(self, repository: ReplicaUserAbstractRepository) -> None:
        """Initialize the directory.

        Args:
            repository: Repository for the module's user replicas.
        """
        self.repository = repository

    async def get_user(self, user_id: UUID) -> UserRef | None:
        """Get a replicated user by ID.

        Args:
            user_id: User ID to look up.

        Returns:
            UserRef: Replicated user data.
            None: If the user is absent from the replica.
        """
        user = await self.repository.get_user(user_id)
        if user is None:
            return None

        return UserRef(user_id=user.id, company_id=user.company_id)
