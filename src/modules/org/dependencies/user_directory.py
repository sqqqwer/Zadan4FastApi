from typing import Annotated

from fastapi import Depends

from src.adapters.dependency import OrgLocalUserDirectoryDependency

from ..adapters.replica_user_directory import OrgReplicaUserDirectory
from ..ports import UserDirectory
from .repositories import ReplicaUserRepositoryDependency


def get_local_user_directory(local_user_directory: OrgLocalUserDirectoryDependency) -> UserDirectory:
    """Get the local user directory.

    Args:
        local_user_directory: Local user directory implementation.

    Returns:
        UserDirectory: User directory.
    """
    return local_user_directory


def get_org_replica_user_directory(repository: ReplicaUserRepositoryDependency) -> OrgReplicaUserDirectory:
    """Get the org replica directory.

    Args:
        repository: Repository for the module's user replicas.

    Returns:
        OrgReplicaUserDirectory: User directory backed by org.users_replica.
    """
    return OrgReplicaUserDirectory(repository=repository)


UserDirectoryDependency = Annotated[UserDirectory, Depends(get_org_replica_user_directory)]
