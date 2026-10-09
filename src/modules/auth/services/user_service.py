import logging
from uuid import UUID

from src.core.resources.exceptions import AuthorizationError
from src.core.services.uow import UowAbstract

from ..repositories import CompanyAbstractRepository, UserAbstractRepository
from ..resources.exceptions import CompanyNotFound, UserNotFound, UserNotHaveMembership
from ..schemas import UserResponse, UserScheme

logger = logging.getLogger(__name__)


class UserService:
    """User service."""

    def __init__(
        self,
        user_repository: UserAbstractRepository,
        company_repository: CompanyAbstractRepository,
        uow: UowAbstract,
    ):
        """Initialize the service.

        Args:
            user_repository: Database repository for user objects.
            company_repository: Database repository for company objects.
            uow: Unit of work for database operations.
        """
        self.user_repository = user_repository
        self.company_repository = company_repository
        self.uow = uow

    async def get_user(self, user_id: UUID, current_company_id: UUID) -> UserResponse:
        """Get the user.

        Args:
            user_id: User ID.
            current_company_id: Current user company ID.

        Returns:
            UserResponse: User response data.

        Raises:
            AuthorizationError: If the user does not have permission for the operation.
            UserNotFound: If the user is not found.
            UserNotHaveMembership: If the user does not have a company membership.
        """
        user = await self.user_repository.get_user_by_id_with_membership(user_id)
        if user is None:
            raise UserNotFound()
        if user.membership is None:
            raise UserNotHaveMembership()
        if user.membership.company_id != current_company_id:
            raise AuthorizationError()
        response = UserResponse(
            id=user.id, first_name=user.first_name, last_name=user.last_name, role=user.membership.role
        )
        logger.info(f"User retrieved: id={response.id}.")
        return response

    async def update_user(self, user_id: UUID, payload: UserScheme) -> UserResponse:
        """Update the user.

        Args:
            user_id: User ID.
            payload: User first and last names.

        Returns:
            UserResponse: User response data.

        Raises:
            UserNotFound: If the user is not found.
            UserNotHaveMembership: If the user does not have a company membership.
        """
        user = await self.user_repository.get_user_by_id_with_membership(user_id)
        if user is None:
            raise UserNotFound()
        if user.membership is None:
            raise UserNotHaveMembership()

        await self.user_repository.update_user(user, payload)

        response = UserResponse(
            id=user.id, first_name=user.first_name, last_name=user.last_name, role=user.membership.role
        )
        await self.uow.commit()
        logger.info(f"User information updated: id={response.id}.")
        return response

    async def get_users_in_company(self, company_id: UUID, limit: int, offset: int) -> list[UserResponse]:
        """Get a list of users in the company.

        Args:
            company_id: Company ID.
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            list[UserResponse]: List of user responses.

        Raises:
            CompanyNotFound: If the company is not found.
        """
        company = await self.company_repository.get_company_by_id(company_id)
        if company is None:
            raise CompanyNotFound()
        members = await self.company_repository.get_members_from_company(company, limit, offset)
        response = [
            UserResponse(
                id=member.user.id, first_name=member.user.first_name, last_name=member.user.last_name, role=member.role
            )
            for member in members
        ]
        logger.info(f"User list retrieved for company '{company.name}'.")
        return response
