from typing import Annotated

from fastapi import Depends

from src.modules.auth.public.dependency import AuthPublicServiceDependency

from .org_local_user_directory import OrgLocalUserDirectory
from .tasks_local_user_directory import TasksLocalUserDirectory


def get_org_local_user_directory(auth_public_service: AuthPublicServiceDependency) -> OrgLocalUserDirectory:
    """Get the org local user directory.

    Args:
        auth_public_service: Public auth service used to get user data.

    Returns:
        OrgLocalUserDirectory: User directory for the org module.
    """
    return OrgLocalUserDirectory(auth_service=auth_public_service)


OrgLocalUserDirectoryDependency = Annotated[OrgLocalUserDirectory, Depends(get_org_local_user_directory)]


def get_tasks_local_user_directory(auth_public_service: AuthPublicServiceDependency) -> TasksLocalUserDirectory:
    """Get the tasks local user directory.

    Args:
        auth_public_service: Public auth service used to get user data.

    Returns:
        TasksLocalUserDirectory: User directory for the tasks module.
    """
    return TasksLocalUserDirectory(auth_service=auth_public_service)


TasksLocalUserDirectoryDependency = Annotated[TasksLocalUserDirectory, Depends(get_tasks_local_user_directory)]
