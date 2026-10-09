import datetime
import hashlib
import logging
import secrets
from uuid import UUID, uuid4

from pydantic import EmailStr

from src.core.config import get_settings
from src.core.events.bus import AbstractEventsBus
from src.core.events.envelope import EventEnvelope
from src.core.events.types import EventType
from src.core.request_context import correlation_id_var
from src.core.resources.enums import RoleEnum
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract

from ..models import Account, Invite
from ..repositories import AccountAbstractRepository, CompanyAbstractRepository, UserAbstractRepository
from ..resources.enums import InvitePurposeEnum
from ..resources.exceptions import (
    AccountNotFound,
    AccountWithEmailAlreadyExists,
    CompanyNotFound,
    CompanyWithThisNameAlreadyExists,
    InviteAlreadyUsed,
    InviteExpired,
    InviteNotFound,
    InviteNotMatchingEmailWithAccount,
    InviteWrongPurpose,
    NewEmailMatchesCurrentEmail,
    SecretsNotExists,
    SecretsPasswordAlreadyExists,
    UserNotFound,
    UserNotHaveMembership,
    UserWithThisAccountAlreadyExists,
)
from ..schemas import (
    AccountEmail,
    AccountEmailResponse,
    CompanyName,
    CompanySignUpEmailConfirmation,
    InviteCreation,
    InviteTokenHashed,
    UserAdminAndCompanyRegistration,
    UserAdminAndCompanyRegistrationResponse,
    UserEmployeeRegistrationResponse,
    UserRegistration,
    UserResponse,
    UserScheme,
)
from .constants import (
    EMAIL_CHANGE_FRONT_PATH,
    EMPLOYEE_INVITE_FRONT_PATH,
    EVENT_PRODUCER,
    INVITE_EXPIRED_TTL_ON_CHANGE_EMAIL,
    INVITE_EXPIRED_TTL_ON_CHECK_EMAIL,
    INVITE_EXPIRED_TTL_ON_EMPLOYEE_CREATE,
)
from .password_service import AbstractPasswordService

logger = logging.getLogger(__name__)


class RegistrationService:
    """Registration service."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        account_repository: AccountAbstractRepository,
        user_repository: UserAbstractRepository,
        company_repository: CompanyAbstractRepository,
        password_service: AbstractPasswordService,
        uow: UowAbstract,
        event_bus: AbstractEventsBus,
    ):
        """Initialize the service.

        Args:
            account_repository: Database repository for account objects.
            user_repository: Database repository for user objects.
            company_repository: Database repository for company objects.
            password_service: Service for hashing and checking passwords.
            uow: Unit of work for database operations.
            event_bus: Event bus used to publish events.
        """
        self.account_repository = account_repository
        self.user_repository = user_repository
        self.company_repository = company_repository
        self.password_service = password_service
        self.uow = uow
        self.event_bus = event_bus

    async def check_account_email(self, account_email: EmailStr, idempotency: IdempotencyAbstractService) -> None:
        """Check that the email is available and create a registration invite.

        Args:
            account_email: Account email to check.
            idempotency: Service for checking and saving idempotent operations.

        Raises:
            AccountWithEmailAlreadyExists: If an account with this email already exists.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
        """
        idempotency_record = await idempotency.check_operation(
            f"company_registration.check_account_email:v1:{account_email}"
        )
        if idempotency_record is not None:
            return

        account_scheme = AccountEmail(account=account_email)
        await self._check_email_available(account_scheme)

        _invite, raw_token = await self._create_invite(
            purpose=InvitePurposeEnum.COMPANY_REGISTRATION,
            ttl=INVITE_EXPIRED_TTL_ON_CHECK_EMAIL,
            recipient_email=account_scheme.email,
        )

        await idempotency.save_operation(response_json={})

        await self.uow.commit()
        logger.info(f"Email {account_email} is available, invite sent by email.")
        logger.warning(f"Sent to email {account_email}: {raw_token}")

    async def company_sign_up_email_confirmation(
        self, payload: CompanySignUpEmailConfirmation, idempotency: IdempotencyAbstractService
    ) -> AccountEmailResponse:
        """Confirm the company registration email and create an account.

        Args:
            payload: Email and invite token for confirmation.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            AccountEmailResponse: Account ID and email.

        Raises:
            AccountWithEmailAlreadyExists: If an account with this email already exists.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            InviteAlreadyUsed: If the invite has already been used.
            InviteExpired: If the invite has expired.
            InviteNotFound: If the invite is not found.
            InviteNotMatchingEmailWithAccount: If the invite does not match the email or account.
            InviteWrongPurpose: If the invite has a different purpose.
        """
        idempotency_record = await idempotency.check_operation(
            "company_registration.company_sign_up_email_confirmation:v1"
        )
        if idempotency_record is not None:
            return AccountEmailResponse.model_validate(idempotency_record)

        invite = await self._get_invite_by_raw_token(payload.invite_token, InvitePurposeEnum.COMPANY_REGISTRATION)
        if invite.recipient_email != payload.email:
            raise InviteNotMatchingEmailWithAccount()

        account_scheme = AccountEmail(account=payload.email)
        await self._check_email_available(account_scheme)

        account = await self.account_repository.create_account(account_scheme)

        invite.used_at = datetime.datetime.now(datetime.UTC)

        await self.uow.flush()

        response = AccountEmailResponse(id=account.id, account=account.email)

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()
        logger.info(f"Email {response.email} confirmed. Account created with id={response.id}.")

        return response

    async def create_company_and_admin(
        self, payload: UserAdminAndCompanyRegistration, idempotency: IdempotencyAbstractService
    ) -> UserAdminAndCompanyRegistrationResponse:
        """Create a company and its admin user.

        Args:
            payload: Company and admin registration data.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            UserAdminAndCompanyRegistrationResponse: Created company and admin data.

        Raises:
            AccountNotFound: If the account is not found.
            CompanyWithThisNameAlreadyExists: If a company with this name already exists.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            UserWithThisAccountAlreadyExists: If a user is already linked to this account.
        """
        idempotency_record = await idempotency.check_operation("company_registration.create_company_and_admin:v1")
        if idempotency_record is not None:
            return UserAdminAndCompanyRegistrationResponse.model_validate(idempotency_record)

        company_name = CompanyName(company_name=payload.company_name)
        check_company_name = await self.company_repository.get_company_by_name(company_name)
        if check_company_name is not None:
            raise CompanyWithThisNameAlreadyExists()

        validated_email = AccountEmail(account=payload.email)
        account = await self.account_repository.get_account_with_secrets_and_user(validated_email)
        if account is None:
            raise AccountNotFound()
        if account.secrets is not None:
            raise UserWithThisAccountAlreadyExists()

        user_valid_data = UserScheme(first_name=payload.first_name, last_name=payload.last_name)
        user = await self.user_repository.create_user(scheme=user_valid_data)

        company_valid_data = CompanyName(company_name=payload.company_name)
        company = await self.company_repository.create_company(scheme=company_valid_data)

        await self.company_repository.create_membership(user=user, company=company, role=RoleEnum.ADMIN)

        hashed_password = self.password_service.password_hash(payload.password)

        await self.account_repository.create_secrets(user, account, hashed_password=hashed_password)
        await self.uow.flush()

        response = UserAdminAndCompanyRegistrationResponse(
            user_id=user.id,
            company_id=company.id,
            company_name=company.name,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()
        logger.info(f"Company '{response.company_name}' and admin user id={response.user_id} created.")

        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=EventType.COMPANY_CREATED,
            aggregate_id=company.id,
            occurred_at=datetime.datetime.now(datetime.UTC),
            schema_version=1,
            correlation_id=UUID(correlation_id_var.get()),
            causation_id=None,
            producer=EVENT_PRODUCER,
            payload={
                "user_id": user.id,
                "company_id": company.id,
                "company_name": company.name,
            },
        )
        logger.info("company.created Event start publish.")
        await self.event_bus.publish(envelope)

        return response

    async def create_user_employee_start(
        self, payload: AccountEmail, company_id: UUID, idempotency: IdempotencyAbstractService
    ) -> UserEmployeeRegistrationResponse:
        """Create an employee account and a registration invite.

        Args:
            payload: Account email data.
            company_id: Company ID.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            UserEmployeeRegistrationResponse: Employee data with the invite token and link.

        Raises:
            AccountWithEmailAlreadyExists: If an account with this email already exists.
            CompanyNotFound: If the company is not found.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
        """
        idempotency_record = await idempotency.check_operation(f"create_employee.create_invite:v1:{company_id}")
        if idempotency_record is not None:
            return UserEmployeeRegistrationResponse.model_validate(idempotency_record)

        company = await self.company_repository.get_company_by_id(company_id)
        if company is None:
            raise CompanyNotFound()

        account_scheme = AccountEmail(account=payload.email)
        await self._check_email_available(account_scheme)

        account = await self.account_repository.create_account(account_scheme)

        _invite, raw_token = await self._create_invite(
            purpose=InvitePurposeEnum.EMPLOYEE_INVITATION,
            ttl=INVITE_EXPIRED_TTL_ON_EMPLOYEE_CREATE,
            recipient_email=account.email,
        )

        user_scheme = UserScheme(
            first_name=None,
            last_name=None,
        )
        user = await self.user_repository.create_user(user_scheme)

        membership = await self.company_repository.create_membership(
            user=user, company=company, role=RoleEnum.EMPLOYEE
        )

        await self.account_repository.create_secrets(user=user, account=account, hashed_password=None)

        await self.uow.flush()

        response = UserEmployeeRegistrationResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            role=membership.role,
            invite_token=raw_token,
            invite_link=self._generate_invite_link(EMPLOYEE_INVITE_FRONT_PATH, raw_token),
            account=account.email,
        )

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()
        logger.info(f"Preliminary user created for employee id={response.id} in company id={company.id}")

        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=EventType.EMPLOYEE_CREATED,
            aggregate_id=user.id,
            occurred_at=datetime.datetime.now(datetime.UTC),
            schema_version=1,
            correlation_id=UUID(correlation_id_var.get()),
            causation_id=None,
            producer=EVENT_PRODUCER,
            payload={
                "user_id": user.id,
                "company_id": company.id,
                "company_name": company.name,
                "user_role": membership.role,
            },
        )
        logger.info("employee.created Event start publish.")
        await self.event_bus.publish(envelope)

        return response

    async def create_user_employee_complete(
        self, payload: UserRegistration, invite_token: str, idempotency: IdempotencyAbstractService
    ) -> UserResponse:
        """Complete employee registration using an invite token.

        Args:
            payload: Employee registration data.
            invite_token: Raw invite token.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            UserResponse: User response data.

        Raises:
            AccountNotFound: If the account is not found.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            InviteAlreadyUsed: If the invite has already been used.
            InviteExpired: If the invite has expired.
            InviteNotFound: If the invite is not found.
            InviteNotMatchingEmailWithAccount: If the invite does not match the email or account.
            InviteWrongPurpose: If the invite has a different purpose.
            SecretsNotExists: If the account secrets are not found.
            SecretsPasswordAlreadyExists: If the account already has a password.
            UserNotHaveMembership: If the user does not have a company membership.
        """
        idempotency_record = await idempotency.check_operation("create_employee.employee_use_invite:v1")
        if idempotency_record is not None:
            return UserResponse.model_validate(idempotency_record)

        invite = await self._get_invite_by_raw_token(invite_token, InvitePurposeEnum.EMPLOYEE_INVITATION)
        if invite.recipient_email != payload.email:
            raise InviteNotMatchingEmailWithAccount()

        validated_email = AccountEmail(account=invite.recipient_email)
        account = await self.account_repository.get_account_with_secrets_and_user(validated_email)
        if account is None:
            raise AccountNotFound()
        if account.secrets is None:
            raise SecretsNotExists()
        if account.secrets.password_hash is not None:
            raise SecretsPasswordAlreadyExists()
        if account.secrets.user.membership is None:
            raise UserNotHaveMembership()

        hashed_password = self.password_service.password_hash(payload.password)
        await self.account_repository.update_secrets_password(account.secrets, hashed_password)

        user_update_scheme = UserScheme(first_name=payload.first_name, last_name=payload.last_name)
        user = await self.user_repository.update_user(account.secrets.user, user_update_scheme)

        invite.used_at = datetime.datetime.now(datetime.UTC)

        response = UserResponse(
            id=user.id, first_name=user.first_name, last_name=user.last_name, role=user.membership.role
        )

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()

        logger.info(
            f"Employee user id={response.id} confirmed registration in company id={user.membership.company_id}."
        )

        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=EventType.EMPLOYEE_REGISTERED,
            aggregate_id=user.id,
            occurred_at=datetime.datetime.now(datetime.UTC),
            schema_version=1,
            correlation_id=UUID(correlation_id_var.get()),
            causation_id=None,
            producer=EVENT_PRODUCER,
            payload={"user_id": user.id, "company_id": user.membership.company_id, "user_role": user.membership.role},
        )
        logger.info("employee.registered Event start publish.")
        await self.event_bus.publish(envelope)

        return response

    async def change_email_start(
        self, payload: AccountEmail, user_id: UUID, idempotency: IdempotencyAbstractService
    ) -> None:
        """Create an invite to confirm an account email change.

        Args:
            payload: Account email data.
            user_id: User ID.
            idempotency: Service for checking and saving idempotent operations.

        Raises:
            AccountNotFound: If the account is not found.
            AccountWithEmailAlreadyExists: If an account with this email already exists.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            NewEmailMatchesCurrentEmail: If the new email matches the current email.
            SecretsNotExists: If the account secrets are not found.
            UserNotFound: If the user is not found.
        """
        idempotency_record = await idempotency.check_operation(f"change_email.start_token_create:v1:{user_id}")
        if idempotency_record is not None:
            return

        account = await self._get_account_by_user_id(user_id)
        if account.email == payload.email:
            raise NewEmailMatchesCurrentEmail()

        await self._check_email_available(payload)

        _invite, raw_token = await self._create_invite(
            purpose=InvitePurposeEnum.EMAIL_CHANGE,
            ttl=INVITE_EXPIRED_TTL_ON_CHANGE_EMAIL,
            recipient_email=payload.email,
            account=account,
        )
        invite_link = self._generate_invite_link(EMAIL_CHANGE_FRONT_PATH, raw_token)

        await idempotency.save_operation(response_json={})

        await self.uow.commit()
        logger.info(
            f"Email change process started for account id={account.id}."
            f"A link was sent to the new email {payload.email}."
        )
        logger.warning(f"Sent to email {payload.email}: {invite_link}")

    async def change_email_complete(
        self, token: str, user_id: UUID, idempotency: IdempotencyAbstractService
    ) -> AccountEmailResponse:
        """Confirm and update the account email.

        Args:
            token: Raw email change token.
            user_id: User ID.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            AccountEmailResponse: Account ID and email.

        Raises:
            AccountNotFound: If the account is not found.
            AccountWithEmailAlreadyExists: If an account with this email already exists.
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            InviteAlreadyUsed: If the invite has already been used.
            InviteExpired: If the invite has expired.
            InviteNotFound: If the invite is not found.
            InviteNotMatchingEmailWithAccount: If the invite does not match the email or account.
            InviteWrongPurpose: If the invite has a different purpose.
            SecretsNotExists: If the account secrets are not found.
            UserNotFound: If the user is not found.
        """
        idempotency_record = await idempotency.check_operation(f"change_email.complete:v1:{user_id}")
        if idempotency_record is not None:
            return AccountEmailResponse.model_validate(idempotency_record)

        account = await self._get_account_by_user_id(user_id)

        invite = await self._get_invite_by_raw_token(token, InvitePurposeEnum.EMAIL_CHANGE)
        if invite.account_id != account.id:
            raise InviteNotMatchingEmailWithAccount()

        account_scheme = AccountEmail(account=invite.recipient_email)
        await self._check_email_available(account_scheme)

        reassigned_account = await self.account_repository.update_account_email(
            account=account, new_email=account_scheme.email
        )

        invite.used_at = datetime.datetime.now(datetime.UTC)

        await self.uow.flush()

        response = AccountEmailResponse(id=reassigned_account.id, account=reassigned_account.email)

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()

        logger.info(f"Email for account id={account.id} was changed.")

        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=EventType.EMPLOYEE_EMAIL_CHANGED,
            aggregate_id=user_id,
            occurred_at=datetime.datetime.now(datetime.UTC),
            schema_version=1,
            correlation_id=UUID(correlation_id_var.get()),
            causation_id=None,
            producer=EVENT_PRODUCER,
            payload={
                "user_id": user_id,
                "account_id": account.id,
                "new_email": reassigned_account.email,
            },
        )
        logger.info("employee.email_changed Event start publish.")
        await self.event_bus.publish(envelope)

        return response

    def _generate_invite_link(self, front_path_name: str, raw_token: str) -> str:
        base_url = get_settings().frontend_url.rstrip("/")
        return f"{base_url}/{front_path_name}/{raw_token}/"

    async def _get_account_by_user_id(self, user_id: UUID) -> Account:
        user = await self.user_repository.get_user_by_id_with_account(user_id)
        if user is None:
            raise UserNotFound()
        if user.secrets is None:
            raise SecretsNotExists()
        if user.secrets.account is None:
            raise AccountNotFound()
        return user.secrets.account

    async def _check_email_available(self, account_scheme: AccountEmail) -> None:
        account = await self.account_repository.get_account(account_scheme)
        if account:
            raise AccountWithEmailAlreadyExists()

    async def _get_invite_by_raw_token(self, token: str, purpose_check: InvitePurposeEnum) -> Invite:
        invite_token_hash = hashlib.sha256(token.encode()).hexdigest()
        invite_token_hash_scheme = InviteTokenHashed(token_hash=invite_token_hash)
        invite = await self.account_repository.get_invite(scheme=invite_token_hash_scheme)
        if invite is None:
            raise InviteNotFound()
        if invite.expired_at <= datetime.datetime.now(datetime.UTC):
            raise InviteExpired()
        if invite.purpose != purpose_check:
            raise InviteWrongPurpose()
        if invite.used_at is not None:
            raise InviteAlreadyUsed()
        return invite

    async def _create_invite(
        self,
        purpose: InvitePurposeEnum,
        ttl: datetime.timedelta,
        recipient_email: EmailStr,
        account: Account | None = None,
    ) -> tuple[Invite, str]:
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expired_at_date = datetime.datetime.now(datetime.UTC) + ttl
        invite_creation_payload = InviteCreation(
            token_hash=token_hash, purpose=purpose, recipient_email=recipient_email, expired_at=expired_at_date
        )
        invite = await self.account_repository.create_invite(invite_creation_payload, account=account)
        return (invite, raw_token)
