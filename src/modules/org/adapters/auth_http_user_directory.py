from http import HTTPStatus
from uuid import UUID

from httpx import AsyncClient, HTTPError
from pydantic import TypeAdapter

from src.core.config import get_settings
from src.core.resources.exceptions import AuthenticationError, AuthorizationError, AuthUnavailableError

from ..public.dto import UserRef


class OrgAuthHttpUserDirectory:
    """User directory backed by the auth HTTP API."""

    def __init__(self, client: AsyncClient, authorization: str) -> None:
        """Initialize the HTTP directory.

        Args:
            client: Shared HTTP client configured with the auth service URL.
            authorization: Authorization header of the current user request.
        """
        self.client = client
        self.authorization = authorization

    async def get_user(self, user_id: UUID) -> UserRef | None:
        """Look up users through the authenticated auth endpoint.

        Args:
            user_id: User ID missing from the replica.

        Returns:
            UserRef | None: Found user, or None if the user is unavailable to the caller.

        Raises:
            AuthenticationError: If auth rejects the access token.
            AuthorizationError: If auth denies access.
            AuthUnavailableError: If the request fails or the response is invalid.
        """
        user_ids = [user_id]
        try:
            response = await self.client.post(
                get_settings().auth_users_lookup_path,
                json={"user_ids": [str(user_id) for user_id in user_ids]},
                headers={"Authorization": self.authorization},
            )
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                raise AuthenticationError()
            if response.status_code == HTTPStatus.FORBIDDEN:
                raise AuthorizationError()
            response.raise_for_status()
            users = TypeAdapter(list[UserRef]).validate_json(response.content)
            if any(user.user_id not in user_ids for user in users):
                raise ValueError("Auth returned an unrequested user")
        except (HTTPError, ValueError) as error:
            raise AuthUnavailableError() from error

        return users[0] if users else None
