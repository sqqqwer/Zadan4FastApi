from abc import ABC, abstractmethod
from typing import override

import jwt
import pydantic

from src.core.resources.exceptions import AuthenticationError
from src.core.schemas.token_claims import AccessTokenClaims


class AbstractJWTDecoderService(ABC):
    """Abstract JWT decoder service."""

    def __init__(self, public_key: str, algorithm: str, audience: str, issuer: str):
        """Initialize the service.

        Args:
            public_key: Public key used to verify JWT signatures.
            algorithm: JWT signing algorithm.
            audience: Expected JWT audience.
            issuer: Expected JWT issuer.
        """
        self.public_key = public_key
        self.algorithm = algorithm
        self.audience = audience
        self.issuer = issuer

    @abstractmethod
    def decode_jwt(self, jwt_token: str) -> AccessTokenClaims:
        """Decode and validate a JWT access token.

        Args:
            jwt_token: Encoded JWT access token.

        Returns:
            AccessTokenClaims: Access token claims.

        Raises:
            AuthenticationError: If the token or its claims are invalid.
        """
        ...


class JWTDecoderService(AbstractJWTDecoderService):
    """JWT decoder service."""

    @override
    def decode_jwt(self, jwt_token: str) -> AccessTokenClaims:
        try:
            decoded_jwt = jwt.decode(
                jwt=jwt_token,
                key=self.public_key,
                algorithms=self.algorithm,
                audience=self.audience,
                issuer=self.issuer,
            )

            claims = AccessTokenClaims.model_validate(decoded_jwt)
            return claims
        except (jwt.InvalidTokenError, pydantic.ValidationError) as error:
            raise AuthenticationError() from error
