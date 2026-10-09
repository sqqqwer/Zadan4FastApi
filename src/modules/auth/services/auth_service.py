import datetime
import hashlib
import logging
import secrets
from uuid import UUID, uuid4

from src.core.config import get_settings
from src.core.resources.enums import RoleEnum
from src.core.schemas.token_claims import AccessTokenClaims
from src.core.services.uow import UowAbstract

from ..repositories import (
    AccountAbstractRepository,
    RefreshSessionAbstractRepository,
)
from ..resources.exceptions import InvalidCredentials
from ..schemas import (
    AccountEmail,
    LoginScheme,
    RefreshSessionCreation,
    RefreshSessionTokenHash,
    RefreshToken,
    TokenResponse,
)
from .constants import ACCESS_TOKEN_EXPIRED_TTL, REFRESH_TOKEN_EXPIRED_TTL
from .jwt_service import AbstractJWTEncoderService
from .password_service import AbstractPasswordService

logger = logging.getLogger(__name__)


class AuthService:
    """Auth service."""

    def __init__(
        self,
        account_repository: AccountAbstractRepository,
        refresh_session_repository: RefreshSessionAbstractRepository,
        password_service: AbstractPasswordService,
        jwt_encoder_service: AbstractJWTEncoderService,
        uow: UowAbstract,
    ):
        """Initialize the service.

        Args:
            account_repository: Database repository for account objects.
            refresh_session_repository: Database repository for refresh session objects.
            password_service: Service for hashing and checking passwords.
            jwt_encoder_service: Service for encoding JWT access tokens.
            uow: Unit of work for database operations.
        """
        self.account_repository = account_repository
        self.refresh_session_repository = refresh_session_repository
        self.password_service = password_service
        self.jwt_encoder_service = jwt_encoder_service
        self.uow = uow

    async def login(self, payload: LoginScheme) -> TokenResponse:
        """Log in using an email and password.

        Args:
            payload: Account email and password.

        Returns:
            TokenResponse: Access and refresh tokens with expiration data.

        Raises:
            InvalidCredentials: If the authentication data is invalid.
        """
        account_schema = AccountEmail(account=payload.email)
        account = await self.account_repository.get_account_with_secrets_and_user(account_schema)
        if account is None:
            raise InvalidCredentials()
        if account.secrets is None:
            raise InvalidCredentials()
        if account.secrets.user.membership is None:
            raise InvalidCredentials()
        if account.secrets.password_hash is None:
            raise InvalidCredentials()

        is_valid_password = self.password_service.password_verify(
            password=payload.password, password_hash=account.secrets.password_hash
        )
        if not is_valid_password:
            raise InvalidCredentials()

        now_time = datetime.datetime.now(datetime.UTC)

        access_token_exp_date = now_time + ACCESS_TOKEN_EXPIRED_TTL

        access_token = self._generate_jwt(
            sub=account.secrets.user_id,
            company_id=account.secrets.user.membership.company_id,
            role=account.secrets.user.membership.role,
            exp=access_token_exp_date,
            now_time=now_time,
        )

        raw_refresh_token = secrets.token_urlsafe(64)
        refresh_token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        refresh_session_scheme = RefreshSessionCreation(
            token_hash=refresh_token_hash,
            created_at=now_time,
            expires_at=now_time + REFRESH_TOKEN_EXPIRED_TTL,
            revoked_at=None,
        )

        await self.refresh_session_repository.create_refresh_session(
            scheme=refresh_session_scheme, user=account.secrets.user
        )

        response = TokenResponse(
            refresh_token=raw_refresh_token,
            access_token=access_token,
            token_type="bearer",
            expires_in=(int(access_token_exp_date.timestamp()) - int(now_time.timestamp())),
        )

        await self.uow.commit()

        logger.info(
            f"Login completed: user_id={account.secrets.user_id}",
        )

        return response

    async def refresh_login(self, payload: RefreshToken) -> TokenResponse:
        """Get a new access token using the refresh token.

        Args:
            payload: Refresh token.

        Returns:
            TokenResponse: Access and refresh tokens with expiration data.

        Raises:
            InvalidCredentials: If the authentication data is invalid.
        """
        raw_refresh_token = payload.refresh_token

        now_time = datetime.datetime.now(datetime.UTC)

        refresh_token_hash = hashlib.sha256(raw_refresh_token.get_secret_value().encode()).hexdigest()

        refresh_session_scheme = RefreshSessionTokenHash(token_hash=refresh_token_hash)
        refresh_session = await self.refresh_session_repository.get_refresh_session_with_user_membership(
            scheme=refresh_session_scheme
        )
        if refresh_session is None:
            raise InvalidCredentials()
        if refresh_session.expires_at <= now_time:
            raise InvalidCredentials()
        if refresh_session.revoked_at is not None:
            raise InvalidCredentials()
        if refresh_session.user.membership is None:
            raise InvalidCredentials()

        access_token_exp_date = now_time + ACCESS_TOKEN_EXPIRED_TTL

        access_token = self._generate_jwt(
            sub=refresh_session.user_id,
            company_id=refresh_session.user.membership.company_id,
            role=refresh_session.user.membership.role,
            exp=access_token_exp_date,
            now_time=now_time,
        )

        response = TokenResponse(
            refresh_token=raw_refresh_token.get_secret_value(),
            access_token=access_token,
            token_type="bearer",
            expires_in=(int(access_token_exp_date.timestamp()) - int(now_time.timestamp())),
        )

        logger.info(
            f"Refresh login completed: user_id={refresh_session.user.id}",
        )

        return response

    def _generate_jwt(
        self,
        sub: UUID,
        company_id: UUID,
        role: RoleEnum,
        exp: datetime.datetime,
        now_time: datetime.datetime,
    ) -> str:
        claims = AccessTokenClaims(
            sub=sub,
            company_id=company_id,
            role=role,
            iss=get_settings().jwt_issuer,
            aud=get_settings().jwt_audience,
            iat=now_time,
            exp=exp,
            jti=uuid4(),
        )
        access_token = self.jwt_encoder_service.get_encoded_jwt(claims)
        return access_token
