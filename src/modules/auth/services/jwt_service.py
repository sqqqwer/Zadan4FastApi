from abc import ABC, abstractmethod
from typing import override

import jwt
from pydantic import SecretStr

from src.core.schemas.token_claims import AccessTokenClaims


class AbstractJWTEncoderService(ABC):
    """Abstract JWT encoder service."""

    def __init__(self, secret_key: SecretStr, algorithm: str):
        """Initialize the service.

        Args:
            secret_key: Key used to sign JWT access tokens.
            algorithm: JWT signing algorithm.
        """
        self.secret_key: SecretStr = secret_key
        self.algorithm: str = algorithm

    @abstractmethod
    def get_encoded_jwt(self, claims: AccessTokenClaims) -> str:
        """Encode access token claims as a JWT.

        Args:
            claims: Access token claims to encode.

        Returns:
            str: Encoded JWT access token.
        """
        ...


class JWTEncoderService(AbstractJWTEncoderService):
    """JWT encoder service."""

    @override
    def get_encoded_jwt(self, claims: AccessTokenClaims) -> str:
        payload = claims.model_dump(exclude={"jti", "sub", "company_id"})
        payload["jti"] = str(claims.jti)
        payload["sub"] = str(claims.sub)
        payload["company_id"] = str(claims.company_id)

        encoded_jwt = jwt.encode(
            payload=payload,
            key=self.secret_key.get_secret_value(),
            algorithm=self.algorithm,
        )
        return encoded_jwt
