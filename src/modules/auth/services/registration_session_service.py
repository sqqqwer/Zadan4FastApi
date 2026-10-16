import datetime
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import override

from ..models import Account, RegistrationSession
from ..repositories import RegistrationSessionAbstractRepository
from ..resources.exceptions import InvalidRegistrationSession
from .constants import REGISTRATION_SESSION_EXPIRED_TTL


class AbstractRegistrationSessionService(ABC):
    """Abstract registration session service."""

    @abstractmethod
    async def create(self, account: Account) -> str:
        """Create a registration session.

        Args:
            account: Confirmed account.

        Returns:
            str: Raw session token.
        """
        ...

    @abstractmethod
    async def get_active(self, token: str) -> RegistrationSession:
        """Get an active registration session.

        Args:
            token: Raw session token.

        Returns:
            RegistrationSession: Active session.

        Raises:
            InvalidRegistrationSession: If the session is missing or expired.
        """
        ...

    @abstractmethod
    async def consume(self, registration_session: RegistrationSession) -> None:
        """Delete a used registration session.

        Args:
            registration_session: Session to delete.
        """
        ...


class RegistrationSessionService(AbstractRegistrationSessionService):
    """Registration session service."""

    def __init__(self, registration_session_repository: RegistrationSessionAbstractRepository):
        """Initialize the service.

        Args:
            registration_session_repository: Database repository for registration sessions.
        """
        self.registration_session_repository = registration_session_repository

    @override
    async def create(self, account: Account) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.datetime.now(datetime.UTC) + REGISTRATION_SESSION_EXPIRED_TTL

        await self.registration_session_repository.create(account, token_hash, expires_at)

        return raw_token

    @override
    async def get_active(self, token: str) -> RegistrationSession:
        if not token:
            raise InvalidRegistrationSession()

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        registration_session = await self.registration_session_repository.get_by_token_hash_for_update(token_hash)

        if registration_session is None:
            raise InvalidRegistrationSession()
        if registration_session.expires_at <= datetime.datetime.now(datetime.UTC):
            raise InvalidRegistrationSession()

        return registration_session

    @override
    async def consume(self, registration_session: RegistrationSession) -> None:
        await self.registration_session_repository.delete(registration_session)
