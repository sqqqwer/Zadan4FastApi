from abc import abstractmethod
from uuid import UUID

from pydantic import EmailStr

from src.core.repositories.base import BaseRepository
from src.core.resources.enums import RoleEnum

from ..models.account import Account
from ..models.company import Company
from ..models.invite import Invite
from ..models.members import Members
from ..models.refresh_session import RefreshSession
from ..models.secrets import Secrets
from ..models.user import User
from ..schemas import (
    AccountEmail,
    CompanyName,
    InviteCreation,
    InviteTokenHashed,
    RefreshSessionCreation,
    RefreshSessionTokenHash,
    RefreshSessionUpdate,
    UserScheme,
)


class AccountAbstractRepository(BaseRepository):
    """Abstract repository for account objects."""

    @abstractmethod
    async def get_invite(self, scheme: InviteTokenHashed) -> Invite | None:
        """Get an invite by its token hash.

        Args:
            scheme: Hashed invite token.

        Returns:
            Invite: Invite object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create_invite(self, scheme: InviteCreation, account: Account | None = None) -> Invite:
        """Create the invite.

        Args:
            scheme: Data for creating an invite.
            account: Account linked to the invite, or None.

        Returns:
            Invite: Invite object.
        """
        ...

    @abstractmethod
    async def get_account(self, scheme: AccountEmail) -> Account | None:
        """Get an account by email.

        Args:
            scheme: Account email data.

        Returns:
            Account: Account object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def update_account_email(self, account: Account, new_email: EmailStr) -> Account:
        """Update the account email.

        Args:
            account: Account object.
            new_email: New account email.

        Returns:
            Account: Account object.
        """
        ...

    @abstractmethod
    async def get_account_with_secrets_and_user(self, scheme: AccountEmail) -> Account | None:
        """Get an account with its secrets and user by email.

        Args:
            scheme: Account email data.

        Returns:
            Account: Account object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create_account(self, scheme: AccountEmail) -> Account:
        """Create the account.

        Args:
            scheme: Account email data.

        Returns:
            Account: Account object.
        """
        ...

    @abstractmethod
    async def create_secrets(self, user: User, account: Account, hashed_password: str | None) -> Secrets:
        """Create the secrets.

        Args:
            user: User object.
            account: Account object.
            hashed_password: Password hash, or None if the password is not set yet.

        Returns:
            Secrets: Account secrets.
        """
        ...

    @abstractmethod
    async def update_secrets_password(self, secrets: Secrets, hashed_password: str) -> Secrets:
        """Update the password hash in the account secrets.

        Args:
            secrets: Account secrets object.
            hashed_password: Password hash.

        Returns:
            Secrets: Account secrets.
        """
        ...


class UserAbstractRepository(BaseRepository):
    """Abstract repository for user objects."""

    @abstractmethod
    async def get_user_by_id(self, id: UUID) -> User | None:
        """Get a user by ID.

        Args:
            id: Object ID.

        Returns:
            User: User object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def get_user_by_id_with_membership(self, id: UUID) -> User | None:
        """Get a user with company membership by ID.

        Args:
            id: Object ID.

        Returns:
            User: User object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def get_user_by_id_with_account(self, id: UUID) -> User | None:
        """Get a user with account data by ID.

        Args:
            id: Object ID.

        Returns:
            User: User object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def get_users_by_id_list(self, ids: list[UUID]) -> list[User]:
        """Get users by their IDs.

        Args:
            ids: User IDs.

        Returns:
            list[User]: List of users.
        """
        ...

    @abstractmethod
    async def create_user(self, scheme: UserScheme) -> User:
        """Create the user.

        Args:
            scheme: User first and last names.

        Returns:
            User: User object.
        """
        ...

    @abstractmethod
    async def update_user(self, user: User, scheme: UserScheme) -> User:
        """Update the user.

        Args:
            user: User object.
            scheme: User first and last names.

        Returns:
            User: User object.
        """
        ...


class CompanyAbstractRepository(BaseRepository):
    """Abstract repository for company objects."""

    @abstractmethod
    async def get_company_by_name(self, scheme: CompanyName) -> Company | None:
        """Get a company by name.

        Args:
            scheme: Company name data.

        Returns:
            Company: Company object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def get_company_by_id(self, id: UUID) -> Company | None:
        """Get a company by ID.

        Args:
            id: Object ID.

        Returns:
            Company: Company object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def get_members_from_company(self, company: Company, limit: int, offset: int) -> list[Members]:
        """Get a list of company memberships.

        Args:
            company: Company object.
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            list[Members]: List of company memberships.
        """
        ...

    @abstractmethod
    async def create_company(self, scheme: CompanyName) -> Company:
        """Create the company.

        Args:
            scheme: Company name data.

        Returns:
            Company: Company object.
        """
        ...

    @abstractmethod
    async def create_membership(self, user: User, company: Company, role: RoleEnum) -> Members:
        """Create the membership.

        Args:
            user: User object.
            company: Company object.
            role: User role in the company.

        Returns:
            Members: Company membership.
        """
        ...


class RefreshSessionAbstractRepository(BaseRepository):
    """Abstract repository for refresh session objects."""

    @abstractmethod
    async def get_refresh_session_with_user_membership(self, scheme: RefreshSessionTokenHash) -> RefreshSession | None:
        """Get a refresh session with user membership by token hash.

        Args:
            scheme: Hashed refresh token.

        Returns:
            RefreshSession: Refresh session.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def update_refresh_session(
        self, refresh_session: RefreshSession, scheme: RefreshSessionUpdate
    ) -> RefreshSession:
        """Update the refresh session.

        Args:
            refresh_session: Refresh session object.
            scheme: Refresh session dates to update.

        Returns:
            RefreshSession: Refresh session.
        """
        ...

    @abstractmethod
    async def create_refresh_session(self, scheme: RefreshSessionCreation, user: User) -> RefreshSession:
        """Create the refresh session.

        Args:
            scheme: Data for creating a refresh session.
            user: User object.

        Returns:
            RefreshSession: Refresh session.
        """
        ...
