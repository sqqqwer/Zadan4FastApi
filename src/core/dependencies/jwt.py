from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import Settings, get_settings
from src.core.resources.enums import RoleEnum
from src.core.resources.exceptions import AuthorizationError
from src.core.schemas.token_claims import AccessTokenClaims
from src.core.services.jwt_decoder import JWTDecoderService

bearer_scheme = HTTPBearer()
JwtSettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_jwt_decoder_service(settings: JwtSettingsDependency) -> JWTDecoderService:
    """Get the JWT decoder service.

    Args:
        settings: Application settings.

    Returns:
        JWTDecoderService: JWT decoder service.
    """
    return JWTDecoderService(
        public_key=settings.jwt_public_key_path.read_text(encoding="utf-8"),
        algorithm=settings.jwt_algorithm,
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


JWTDecoderServiceDependency = Annotated[JWTDecoderService, Depends(get_jwt_decoder_service)]


def get_current_claims(
    jwt_decoder: JWTDecoderServiceDependency,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> AccessTokenClaims:
    """Get current user claims from the bearer token.

    Args:
        jwt_decoder: Service for decoding JWT access tokens.
        credentials: Bearer token from the Authorization header.

    Returns:
        AccessTokenClaims: Access token claims.

    Raises:
        AuthenticationError: If the token or its claims are invalid.
    """
    return jwt_decoder.decode_jwt(jwt_token=credentials.credentials)


AccessTokenClaimsDependency = Annotated[AccessTokenClaims, Depends(get_current_claims)]


def require_admin(claims: AccessTokenClaimsDependency) -> AccessTokenClaims:
    """Check that the current user is an admin.

    Args:
        claims: Current user access token claims.

    Returns:
        AccessTokenClaims: Access token claims.

    Raises:
        AuthorizationError: If the current user is not an admin.
    """
    if claims.role != RoleEnum.ADMIN:
        raise AuthorizationError()
    return claims


RequireAdminClaimsDependency = Annotated[AccessTokenClaims, Depends(require_admin)]
