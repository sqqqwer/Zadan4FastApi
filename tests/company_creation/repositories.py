from dataclasses import dataclass, field
from typing import override
from uuid import UUID, uuid4

from pydantic import EmailStr

from src.core.resources.enums import RoleEnum
from src.modules.auth.models.account import Account
from src.modules.auth.models.company import Company
from src.modules.auth.models.invite import Invite
from src.modules.auth.models.members import Members
from src.modules.auth.models.refresh_session import RefreshSession
from src.modules.auth.models.secrets import Secrets
from src.modules.auth.models.user import User
from src.modules.auth.repositories.abstracts import (
    AccountAbstractRepository,
    BaseRepository,
    CompanyAbstractRepository,
    RefreshSessionAbstractRepository,
    UserAbstractRepository,
)
from src.modules.auth.schemas import (
    AccountEmail,
    CompanyName,
    InviteCreation,
    InviteTokenHashed,
    RefreshSessionCreation,
    RefreshSessionTokenHash,
    RefreshSessionUpdate,
    UserScheme,
)


@dataclass
class FakeDatabase:
    """In-memory storage for test objects."""

    accounts: dict[UUID, Account] = field(default_factory=dict)
    invites: dict[UUID, Invite] = field(default_factory=dict)
    secrets: dict[UUID, Secrets] = field(default_factory=dict)
    members: dict[UUID, Members] = field(default_factory=dict)
    companies: dict[UUID, Company] = field(default_factory=dict)
    refresh_sessions: dict[UUID, RefreshSession] = field(default_factory=dict)
    users: dict[UUID, User] = field(default_factory=dict)


class BaseMockRepository(BaseRepository):
    """Base repository using the fake database."""

    def __init__(self, db: FakeDatabase):
        """Initialize the repository.

        Args:
            db: Fake database used by the repository.
        """
        self.db = db


class AccountMockRepository(BaseMockRepository, AccountAbstractRepository):
    """Test repository for account objects."""

    @override
    async def get_invite(self, scheme: InviteTokenHashed) -> Invite | None:
        result_invite = None
        for invite in self.db.invites.values():
            if invite.token_hash == scheme.token_hash:
                result_invite = invite
        return result_invite

    @override
    async def create_invite(self, scheme: InviteCreation, account: Account | None = None) -> Invite:
        invite = Invite(
            **scheme.model_dump(), id=uuid4(), account=account, account_id=account.id if account is not None else None
        )
        self.db.invites[invite.id] = invite
        return invite

    @override
    async def get_account(self, scheme: AccountEmail) -> Account | None:
        result_account = None
        for account in self.db.accounts.values():
            if account.email == scheme.email:
                result_account = account
        return result_account

    @override
    async def update_account_email(self, account: Account, new_email: EmailStr) -> Account:
        account.email = new_email
        return account

    @override
    async def get_account_with_secrets_and_user(self, scheme: AccountEmail) -> Account | None:
        return await self.get_account(scheme)

    @override
    async def create_account(self, scheme: AccountEmail) -> Account:
        account = Account(**scheme.model_dump(), id=uuid4())
        self.db.accounts[account.id] = account
        return account

    @override
    async def create_secrets(self, user: User, account: Account, hashed_password: str | None) -> Secrets:
        secrets = Secrets(
            user=user,
            account=account,
            password_hash=hashed_password,
            id=uuid4(),
            user_id=user.id,
            account_id=account.id,
        )
        self.db.secrets[secrets.id] = secrets
        return secrets

    @override
    async def update_secrets_password(self, secrets: Secrets, hashed_password: str) -> Secrets:
        secrets.password_hash = hashed_password
        return secrets


class UserMockRepository(BaseMockRepository, UserAbstractRepository):
    """Test repository for user objects."""

    @override
    async def get_user_by_id(self, id: UUID) -> User | None:
        return self.db.users.get(id, None)

    @override
    async def get_user_by_id_with_membership(self, id: UUID) -> User | None:
        return await self.get_user_by_id(id)

    @override
    async def get_user_by_id_with_account(self, id: UUID) -> User | None:
        return await self.get_user_by_id(id)

    @override
    async def get_users_by_id_list(self, ids: list[UUID]) -> list[User]:
        requested_ids = set(ids)

        return [user for user_id, user in self.db.users.items() if user_id in requested_ids]

    @override
    async def create_user(self, scheme: UserScheme) -> User:
        user = User(**scheme.model_dump(), id=uuid4())
        self.db.users[user.id] = user
        return user

    @override
    async def update_user(self, user: User, scheme: UserScheme) -> User:
        user.first_name = scheme.first_name
        user.last_name = scheme.last_name
        return user


class CompanyMockRepository(BaseMockRepository, CompanyAbstractRepository):
    """Test repository for company objects."""

    @override
    async def get_company_by_name(self, scheme: CompanyName) -> Company | None:
        result_company = None
        for company in self.db.companies.values():
            if company.name == scheme.company_name:
                result_company = company
        return result_company

    @override
    async def get_company_by_id(self, id: UUID) -> Company | None:
        return self.db.companies.get(id, None)

    @override
    async def get_members_from_company(self, company: Company, limit: int, offset: int) -> list[Members]:
        members = [member for member in self.db.members.values() if member.company_id == company.id]

        role_order = {
            RoleEnum.ADMIN: 0,
            RoleEnum.EMPLOYEE: 1,
        }

        members.sort(
            key=lambda member: (
                role_order.get(member.role, 2),
                member.id,
            )
        )

        return members[offset : offset + limit]

    @override
    async def create_company(self, scheme: CompanyName) -> Company:
        company = Company(name=scheme.company_name, id=uuid4())
        self.db.companies[company.id] = company
        return company

    @override
    async def create_membership(self, user: User, company: Company, role: RoleEnum) -> Members:
        member = Members(user=user, company=company, role=role, id=uuid4(), user_id=user.id, company_id=company.id)
        self.db.members[member.id] = member
        return member


class RefreshSessionMockRepository(BaseMockRepository, RefreshSessionAbstractRepository):
    """Test repository for refresh session objects."""

    @override
    async def get_refresh_session_with_user_membership(self, scheme: RefreshSessionTokenHash) -> RefreshSession | None:
        result_refresh_session = None
        for refresh_session in self.db.refresh_sessions.values():
            if refresh_session.token_hash == scheme.token_hash:
                result_refresh_session = refresh_session
        return result_refresh_session

    @override
    async def update_refresh_session(
        self, refresh_session: RefreshSession, scheme: RefreshSessionUpdate
    ) -> RefreshSession:
        refresh_session.created_at = scheme.created_at
        refresh_session.expires_at = scheme.expires_at
        refresh_session.revoked_at = scheme.revoked_at
        return refresh_session

    @override
    async def create_refresh_session(self, scheme: RefreshSessionCreation, user: User) -> RefreshSession:
        refresh_session = RefreshSession(**scheme.model_dump(), id=uuid4(), user=user, user_id=user.id)
        self.db.refresh_sessions[refresh_session.id] = refresh_session
        return refresh_session
