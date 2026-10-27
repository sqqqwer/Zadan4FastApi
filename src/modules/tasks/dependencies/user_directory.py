from typing import Annotated

from fastapi import Depends

from ..adapters.replica_user_directory import TasksReplicaUserDirectory
from ..ports import UserDirectory
from .reposiroties import ReplicaUserRepositoryDependency


def get_tasks_replica_user_directory(repository: ReplicaUserRepositoryDependency) -> TasksReplicaUserDirectory:
    """Get the tasks replica directory.

    Args:
        repository: Repository for the module's user replicas.

    Returns:
        TasksReplicaUserDirectory: User directory backed by tasks.users_replica.
    """
    return TasksReplicaUserDirectory(repository=repository)


UserDirectoryDependency = Annotated[UserDirectory, Depends(get_tasks_replica_user_directory)]
