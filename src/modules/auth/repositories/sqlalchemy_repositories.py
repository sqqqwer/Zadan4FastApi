from typing import override
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
from .abstracts import (
    AccountAbstractRepository,
    CompanyAbstractRepository,
    RefreshSessionAbstractRepository,
    UserAbstractRepository,
)


class AuthBaseSqlAlchemyRepository(BaseRepository):
    """SQLAlchemy repository for auth objects."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: Database session used by the repository.
        """
        self.session = session


class AccountSqlAlchemyRepository(AuthBaseSqlAlchemyRepository, AccountAbstractRepository):
    """SQLAlchemy repository for account objects."""

    @override
    async def get_invite(self, scheme: InviteTokenHashed) -> Invite | None:
        stmt = select(Invite).where(Invite.token_hash == scheme.token_hash).with_for_update()
        invite = await self.session.execute(stmt)
        return invite.scalar_one_or_none()

    @override
    async def create_invite(self, scheme: InviteCreation, account: Account | None = None) -> Invite:
        invite = Invite(**scheme.model_dump(), account=account)
        self.session.add(invite)
        return invite

    @override
    async def get_account(self, scheme: AccountEmail) -> Account | None:
        stmt = select(Account).where(Account.email == scheme.email)
        account = await self.session.execute(stmt)
        return account.scalar_one_or_none()

    @override
    async def update_account_email(self, account: Account, new_email: EmailStr) -> Account:
        account.email = new_email
        return account

    @override
    async def get_account_with_secrets_and_user(self, scheme: AccountEmail) -> Account | None:
        stmt = (
            select(Account)
            .options(joinedload(Account.secrets).joinedload(Secrets.user).joinedload(User.membership))
            .where(Account.email == scheme.email)
        )
        account = await self.session.execute(stmt)
        return account.scalar_one_or_none()

    @override
    async def create_account(self, scheme: AccountEmail) -> Account:
        account = Account(**scheme.model_dump())
        self.session.add(account)
        return account

    @override
    async def create_secrets(self, user: User, account: Account, hashed_password: str | None) -> Secrets:
        secrets = Secrets(user=user, account=account, password_hash=hashed_password)
        self.session.add(secrets)
        return secrets

    @override
    async def update_secrets_password(self, secrets: Secrets, hashed_password: str) -> Secrets:
        secrets.password_hash = hashed_password
        return secrets


class UserSqlAlchemyRepository(AuthBaseSqlAlchemyRepository, UserAbstractRepository):
    """SQLAlchemy repository for user objects."""

    @override
    async def get_user_by_id(self, id: UUID) -> User | None:
        user = await self.session.get(User, id)
        return user

    @override
    async def get_user_by_id_with_membership(self, id: UUID) -> User | None:
        stmt = select(User).options(joinedload(User.membership)).where(User.id == id)
        user = await self.session.execute(stmt)
        return user.scalar_one_or_none()

    @override
    async def get_user_by_id_with_account(self, id: UUID) -> User | None:
        stmt = select(User).options(joinedload(User.secrets).joinedload(Secrets.account)).where(User.id == id)
        user = await self.session.execute(stmt)
        return user.scalar_one_or_none()

    @override
    async def get_users_by_id_list(self, ids: list[UUID]) -> list[User]:
        stmt = select(User).options(joinedload(User.membership)).where(User.id.in_(ids))
        users = await self.session.scalars(stmt)
        return list(users.all())

    @override
    async def create_user(self, scheme: UserScheme) -> User:
        user = User(**scheme.model_dump())
        self.session.add(user)
        return user

    @override
    async def update_user(self, user: User, scheme: UserScheme) -> User:
        user.first_name = scheme.first_name
        user.last_name = scheme.last_name
        return user


class CompanySqlAlchemyRepository(AuthBaseSqlAlchemyRepository, CompanyAbstractRepository):
    """SQLAlchemy repository for company objects."""

    @override
    async def get_company_by_name(self, scheme: CompanyName) -> Company | None:
        stmt = select(Company).where(Company.name == scheme.company_name)
        company = await self.session.execute(stmt)
        return company.scalar_one_or_none()

    @override
    async def get_company_by_id(self, id: UUID) -> Company | None:
        company = await self.session.get(Company, id)
        return company

    @override
    async def get_members_from_company(self, company: Company, limit: int, offset: int) -> list[Members]:
        stmt = (
            select(Members)
            .options(joinedload(Members.user))
            .where(Members.company_id == company.id)
            .order_by(
                case(
                    (Members.role == RoleEnum.ADMIN, 0),
                    (Members.role == RoleEnum.EMPLOYEE, 1),
                    else_=2,
                ),
                Members.id,
            )
            .offset(offset)
            .limit(limit)
        )
        members = await self.session.scalars(stmt)
        return list(members.all())

    @override
    async def create_company(self, scheme: CompanyName) -> Company:
        company = Company(name=scheme.company_name)
        self.session.add(company)
        return company

    @override
    async def create_membership(self, user: User, company: Company, role: RoleEnum) -> Members:
        member = Members(user=user, company=company, role=role)
        self.session.add(member)
        return member


class RefreshSessionSqlAlchemyRepository(AuthBaseSqlAlchemyRepository, RefreshSessionAbstractRepository):
    """SQLAlchemy repository for refresh session objects."""

    @override
    async def get_refresh_session_with_user_membership(self, scheme: RefreshSessionTokenHash) -> RefreshSession | None:
        stmt = (
            select(RefreshSession)
            .options(joinedload(RefreshSession.user).joinedload(User.membership))
            .where(RefreshSession.token_hash == scheme.token_hash)
        )
        refresh_session = await self.session.execute(stmt)
        return refresh_session.scalar_one_or_none()

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
        refresh_session = RefreshSession(**scheme.model_dump(), user=user)
        self.session.add(refresh_session)
        return refresh_session
