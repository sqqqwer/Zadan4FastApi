import logging
from uuid import UUID

from ..repositories import CompanyAbstractRepository, UserAbstractRepository
from .dto import CompanyRef, UserRef

logger = logging.getLogger(__name__)


class AuthPublicService:
    """Service for getting auth data from other modules."""

    def __init__(
        self,
        user_repository: UserAbstractRepository,
        company_repository: CompanyAbstractRepository,
    ):
        """Initialize the service.

        Args:
            user_repository: Database repository for user objects.
            company_repository: Database repository for company objects.
        """
        self.user_repository = user_repository
        self.company_repository = company_repository

    async def get_user(self, user_id: UUID) -> UserRef | None:
        """Get the user.

        Args:
            user_id: User ID.

        Returns:
            UserRef: User data.
            None: If the user is not found or has no company membership.
        """
        user = await self.user_repository.get_user_by_id_with_membership(user_id)
        if user is None:
            return None
        if user.membership is None:
            logger.warning(f"User has no membership: user_id={user_id}")
            return None

        response = UserRef(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.membership.role,
            company_id=user.membership.company_id,
        )
        return response

    async def get_many_users(self, user_ids: list[UUID]) -> dict[UUID, UserRef]:
        """Get users by their IDs.

        Args:
            user_ids: User IDs.

        Returns:
            dict[UUID, UserRef]: Users with company membership, indexed by their IDs.
        """
        users = await self.user_repository.get_users_by_id_list(user_ids)
        user_wo_membership_ids: list[UUID] = []
        response: dict[UUID, UserRef] = {}
        for user in users:
            if user.membership is None:
                user_wo_membership_ids.append(user.id)
                continue
            response[user.id] = UserRef(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.membership.role,
                company_id=user.membership.company_id,
            )

        if len(user_wo_membership_ids) > 0:
            logger.warning(f"Users with no membership: user_ids={user_wo_membership_ids}")
        return response

    async def get_company(self, company_id: UUID) -> CompanyRef | None:
        """Get the company.

        Args:
            company_id: Company ID.

        Returns:
            CompanyRef: Company data.
            None: If the object is not found.
        """
        company = await self.company_repository.get_company_by_id(company_id)
        if company is None:
            return None

        response = CompanyRef(id=company.id, name=company.name)
        return response
