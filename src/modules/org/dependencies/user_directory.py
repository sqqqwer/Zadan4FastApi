from typing import Annotated

from fastapi import Depends

from ..adapters.replica_user_directory import OrgReplicaUserDirectory
from ..ports import UserDirectory
from .repositories import ReplicaUserRepositoryDependency


def get_org_replica_user_directory(repository: ReplicaUserRepositoryDependency) -> OrgReplicaUserDirectory:
    """Get the org replica directory.

    Args:
        repository: Repository for the module's user replicas.

    Returns:
        OrgReplicaUserDirectory: User directory backed by org.users_replica.
    """
    return OrgReplicaUserDirectory(repository=repository)


UserDirectoryDependency = Annotated[UserDirectory, Depends(get_org_replica_user_directory)]
