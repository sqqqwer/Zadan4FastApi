from typing import Annotated

from fastapi import Depends

from src.adapters.dependency import TasksLocalUserDirectoryDependency

from ..ports import UserDirectory


def get_local_user_directory(local_user_directory: TasksLocalUserDirectoryDependency) -> UserDirectory:
    """Get the local user directory.

    Args:
        local_user_directory: Local user directory implementation.

    Returns:
        UserDirectory: User directory.
    """
    return local_user_directory


UserDirectoryDependency = Annotated[UserDirectory, Depends(get_local_user_directory)]
