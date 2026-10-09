from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.auth.public.service import AuthPublicService
from src.modules.org.public.dto import UserRef as OrgUserRef

if TYPE_CHECKING:
    from src.modules.auth.public.dto import UserRef as AuthUserRef


class OrgLocalUserDirectory:
    """User directory for the org module using the auth service."""

    def __init__(self, auth_service: AuthPublicService):
        """Initialize the user directory.

        Args:
            auth_service: Public auth service used to get user data.
        """
        self._auth_service = auth_service

    async def get_user(self, user_id: UUID) -> OrgUserRef | None:
        """Get the user.

        Args:
            user_id: User ID.

        Returns:
            OrgUserRef: User data for the org module.
            None: If the user is not found or has no company membership.
        """
        user: AuthUserRef | None = await self._auth_service.get_user(user_id)
        return (
            OrgUserRef(
                user_id=user.id,
                company_id=user.company_id,
            )
            if user is not None
            else None
        )
