from typing import Annotated

from fastapi import Depends

from ..services.password_service import AbstractPasswordService, PasswordService


def get_password_service() -> AbstractPasswordService:
    """Get the password service.

    Returns:
        AbstractPasswordService: Password service.
    """
    return PasswordService()


PasswordHasherDependency = Annotated[AbstractPasswordService, Depends(get_password_service)]
