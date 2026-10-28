from typing import Annotated

from fastapi import Depends

from src.core.dependencies.http import AuthHttpClientDependency
from src.core.dependencies.jwt import BearerCredentialsDependency

from ..adapters.auth_http_user_directory import OrgAuthHttpUserDirectory
from ..adapters.replica_user_directory import OrgReplicaUserDirectory
from ..ports import UserDirectory
from .repositories import ReplicaUserRepositoryDependency


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
    return OrgAuthHttpUserDirectory(client=client, authorization=f"Bearer {credentials.credentials}")


AuthHttpUserDirectoryDependency = Annotated[UserDirectory, Depends(get_auth_http_user_directory)]


def get_org_replica_user_directory(
    repository: ReplicaUserRepositoryDependency, fallback: AuthHttpUserDirectoryDependency
) -> OrgReplicaUserDirectory:
    """Get the org replica directory.

    Args:
        repository: Repository for the module's user replicas.
        fallback: HTTP user directory used when the replica has no record.

    Returns:
        OrgReplicaUserDirectory: User directory backed by org.users_replica.
    """
    return OrgReplicaUserDirectory(repository=repository, fallback=fallback)


UserDirectoryDependency = Annotated[UserDirectory, Depends(get_org_replica_user_directory)]
