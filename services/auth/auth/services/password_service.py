from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, override

from pydantic import SecretStr

from ..security.password_hasher import password_hasher

if TYPE_CHECKING:
    from pwdlib import PasswordHash


class AbstractPasswordService(ABC):
    """Abstract password service."""

    @abstractmethod
    def password_hash(self, password: SecretStr) -> str:
        """Hash the password.

        Args:
            password: Password to hash or check.

        Returns:
            str: Password hash.
        """
        ...

    @abstractmethod
    def password_verify(self, password: SecretStr, password_hash: str) -> bool:
        """Check that the password matches the stored hash.

        Args:
            password: Password to hash or check.
            password_hash: Stored password hash.

        Returns:
            bool: True if the password matches the hash, otherwise False.
        """
        ...


class PasswordService(AbstractPasswordService):
    """Password service."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.password_hasher: PasswordHash = password_hasher

    @override
    def password_hash(self, password: SecretStr) -> str:
        password_secret_str = password.get_secret_value()
        hashed_password = self.password_hasher.hash(password_secret_str)
        return hashed_password

    @override
    def password_verify(self, password: SecretStr, password_hash: str) -> bool:
        return self.password_hasher.verify(
            password.get_secret_value(),
            password_hash,
        )
