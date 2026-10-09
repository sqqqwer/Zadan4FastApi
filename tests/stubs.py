
from uuid import UUID

from src.modules.org.public.dto import UserRef as OrgUserRef
from src.modules.tasks.public.dto import UserRef as TasksUserRef


class StubTasksUserDirectory:
    """Stub user directory for the tasks module."""

    def __init__(self, company_id: UUID):
        """Initialize the stub user directory.

        Args:
            company_id: Company ID used for stub users.
        """
        self.company_id = company_id

    async def get_many(self, user_ids: list[UUID]) -> dict[UUID, TasksUserRef]:
        """Get stub user data for the given IDs.

        Args:
            user_ids: User IDs.

        Returns:
            dict[UUID, TasksUserRef]: Stub users indexed by their IDs.
        """
        return {
            user_id: TasksUserRef(
                user_id=user_id,
                full_name="Test Test",
                company_id=self.company_id,
            ) for user_id in user_ids
        }

class StubOrgUserDirectory:
    """Stub user directory for the org module."""

    def __init__(self, company_id: UUID):
        """Initialize the stub user directory.

        Args:
            company_id: Company ID used for stub users.
        """
        self.company_id = company_id

    async def get_user(self, user_id: UUID) -> OrgUserRef:
        """Get stub user data for the given ID.

        Args:
            user_id: User ID.

        Returns:
            OrgUserRef: Stub user data for the requested ID.
        """
        return OrgUserRef(
            user_id=user_id,
            company_id=self.company_id,
        )
