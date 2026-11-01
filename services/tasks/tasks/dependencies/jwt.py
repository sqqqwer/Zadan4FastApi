from typing import Annotated

from fastapi import Depends

from shared.jwt.claims_scheme import AccessTokenClaims
from shared.jwt.dependencies import make_jwt_dependencies
from shared.jwt.service import JWTDecoderService

from ..config import Settings, get_settings

JwtSettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_jwt_decoder_service(settings: JwtSettingsDependency) -> JWTDecoderService:
    """Build a JWT decoder using this service's public key and settings."""
    return JWTDecoderService(
        public_key=settings.jwt_public_key_path.read_text(encoding="utf-8"),
        algorithm=settings.jwt_algorithm,
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


get_current_claims, require_admin = make_jwt_dependencies(get_jwt_decoder_service)

AccessTokenClaimsDependency = Annotated[AccessTokenClaims, Depends(get_current_claims)]
RequireAdminClaimsDependency = Annotated[AccessTokenClaims, Depends(require_admin)]
