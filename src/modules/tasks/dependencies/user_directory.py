from typing import Annotated

from fastapi import Depends

from src.core.dependencies.http import AuthHttpClientDependency
from src.core.dependencies.jwt import BearerCredentialsDependency

from ..adapters.auth_http_user_directory import TasksAuthHttpUserDirectory
from ..adapters.replica_user_directory import TasksReplicaUserDirectory
from ..ports import UserDirectory
from .reposiroties import ReplicaUserRepositoryDependency


def get_auth_http_user_directory(
    credentials: BearerCredentialsDependency, client: AuthHttpClientDependency
) -> UserDirectory:
    """Get the HTTP fallback for the current user request.

    Args:
        credentials: Original bearer token extracted by the shared JWT dependency.
        client: Shared HTTP client configured for auth.

    Returns:
        UserDirectory: HTTP user directory for this module.
    """
    return TasksAuthHttpUserDirectory(client=client, authorization=f"Bearer {credentials.credentials}")


AuthHttpUserDirectoryDependency = Annotated[UserDirectory, Depends(get_auth_http_user_directory)]


def get_tasks_replica_user_directory(
    repository: ReplicaUserRepositoryDependency, fallback: AuthHttpUserDirectoryDependency
) -> TasksReplicaUserDirectory:
    """Get the tasks replica directory.

    Args:
        repository: Repository for the module's user replicas.
        fallback: HTTP user directory used when the replica has no record.

    Returns:
        TasksReplicaUserDirectory: User directory backed by tasks.users_replica.
    """
    return TasksReplicaUserDirectory(repository=repository, fallback=fallback)


UserDirectoryDependency = Annotated[UserDirectory, Depends(get_tasks_replica_user_directory)]
