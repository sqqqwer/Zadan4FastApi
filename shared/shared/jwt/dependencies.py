from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.resources.enums import RoleEnum
from shared.resources.exceptions import AuthorizationError

from .claims_scheme import AccessTokenClaims
from .service import JWTDecoderService

bearer_scheme = HTTPBearer()
BearerCredentialsDependency = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


def make_jwt_dependencies(
    decoder_dependency: Callable[..., JWTDecoderService],
) -> tuple[Callable[..., AccessTokenClaims], Callable[..., AccessTokenClaims]]:
    """Build claims and admin dependencies using the service's decoder provider.

    Args:
        decoder_dependency: Dependency that creates the configured JWT decoder.

    Returns:
        tuple: Current claims dependency followed by the admin claims dependency.
    """

    def get_current_claims(
        jwt_decoder: Annotated[JWTDecoderService, Depends(decoder_dependency)],
        credentials: BearerCredentialsDependency,
    ) -> AccessTokenClaims:
        """Decode and validate the current request's bearer token."""
        return jwt_decoder.decode_jwt(jwt_token=credentials.credentials)

    def require_admin(
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
    ) -> AccessTokenClaims:
        """Return validated claims or reject a user without the admin role."""
        if claims.role != RoleEnum.ADMIN:
            raise AuthorizationError()
        return claims

    return get_current_claims, require_admin
