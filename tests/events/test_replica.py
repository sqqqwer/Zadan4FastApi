import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient, MockTransport, Response

from org.adapters.auth_http_user_directory import OrgAuthHttpUserDirectory
from org.adapters.replica_user_directory import OrgReplicaUserDirectory
from org.events import save_user_replica as save_org_replica
from org.models.users_replica import UsersReplicaOrg
from org.repositories.sqlalchemy_repositories import ReplicaUserSqlAlchemyRepository as OrgReplicaRepository
from shared.resources.exceptions import AuthUnavailableError
from tasks.adapters.auth_http_user_directory import TasksAuthHttpUserDirectory
from tasks.adapters.replica_user_directory import TasksReplicaUserDirectory
from tasks.events import save_user_replica as save_tasks_replica
from tasks.models.users_replica import UsersReplicaTasks
from tasks.repositories.sqlalchemy_repositories import ReplicaUserSqlAlchemyRepository as TasksReplicaRepository
from tasks.resources.constants import USER_SNAPSHOT_V2


@pytest.mark.parametrize("service_name", ["org", "tasks"])
async def test_old_snapshot_does_not_overwrite_replica(service_name, envelope, test_db):
    """Out-of-order delivery cannot restore stale names or company data."""
    handler = save_org_replica if service_name == "org" else save_tasks_replica
    model = UsersReplicaOrg if service_name == "org" else UsersReplicaTasks
    await handler(envelope, test_db)
    await test_db.flush()
    older = envelope.model_copy(
        update={
            "event_id": uuid4(),
            "occurred_at": envelope.occurred_at - timedelta(seconds=1),
            "payload": {**envelope.payload, "full_name": "Stale Name", "company_id": str(uuid4()), "is_active": False},
        }
    )

    await handler(older, test_db)
    await test_db.flush()
    test_db.expire_all()

    user = await test_db.get(model, envelope.aggregate_id)
    assert user.full_name == "Test User"
    assert user.company_id == UUID(envelope.payload["company_id"])
    assert user.is_active is True
    assert user.last_event_at == envelope.occurred_at


@pytest.mark.parametrize("schema_version", [1, 2])
async def test_tasks_consumer_accepts_both_snapshot_versions(
    consumer, envelope, make_message, test_db, schema_version
):
    """Both supported payload formats produce the same readable local name."""
    if schema_version == USER_SNAPSHOT_V2:
        payload = {key: value for key, value in envelope.payload.items() if key != "full_name"}
        payload.update(first_name="Test", last_name="User")
        envelope = envelope.model_copy(update={"schema_version": schema_version, "payload": payload})
    await consumer.bus.subscribe(envelope.event_type, save_tasks_replica)
    consumer.consumer.messages = [make_message(envelope.model_dump_json().encode())]

    await consumer.run()

    user = await test_db.get(UsersReplicaTasks, envelope.aggregate_id)
    assert user.full_name == "Test User"
    assert user.company_id == UUID(envelope.payload["company_id"])
    assert user.last_event_at == envelope.occurred_at
    consumer.consumer.commit.assert_awaited_once()


@pytest.mark.parametrize("service_name", ["org", "tasks"])
@pytest.mark.parametrize("replica_hit", [True, False])
async def test_user_directory_uses_http_only_for_replica_miss(service_name, envelope, test_db, replica_hit):
    """A known user is read locally; only a missing user is sent to the authenticated fallback."""
    requests = []
    user_id = envelope.aggregate_id
    company_id = UUID(envelope.payload["company_id"])
    model = UsersReplicaOrg if service_name == "org" else UsersReplicaTasks
    if replica_hit:
        test_db.add(
            model(
                id=user_id,
                company_id=company_id,
                full_name="Test User",
                is_active=True,
                last_event_at=envelope.occurred_at,
            )
        )
        await test_db.flush()

    def lookup(request):
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path == "/auth/api/v1/users/lookup"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert json.loads(request.content) == {"user_ids": [str(user_id)]}
        return Response(200, json=[{"user_id": str(user_id), "company_id": str(company_id), "full_name": "Test User"}])

    async with AsyncClient(base_url="http://auth:8000", transport=MockTransport(lookup)) as client:
        if service_name == "org":
            directory = OrgReplicaUserDirectory(
                OrgReplicaRepository(test_db), OrgAuthHttpUserDirectory(client, "Bearer test-token")
            )
            user = await directory.get_user(user_id)
        else:
            directory = TasksReplicaUserDirectory(
                TasksReplicaRepository(test_db), TasksAuthHttpUserDirectory(client, "Bearer test-token")
            )
            user = (await directory.get_many([user_id]))[user_id]

    assert user.user_id == user_id and user.company_id == company_id
    assert len(requests) == (0 if replica_hit else 1)


@pytest.mark.parametrize("service_name", ["org", "tasks"])
async def test_replica_miss_reports_unavailable_auth(service_name, envelope, test_db):
    """A failed fallback cannot turn an unknown user into a valid assignment."""
    async with AsyncClient(
        base_url="http://auth:8000", transport=MockTransport(lambda request: Response(503))
    ) as client:
        with pytest.raises(AuthUnavailableError):
            if service_name == "org":
                directory = OrgReplicaUserDirectory(
                    OrgReplicaRepository(test_db), OrgAuthHttpUserDirectory(client, "token")
                )
                await directory.get_user(envelope.aggregate_id)
            else:
                directory = TasksReplicaUserDirectory(
                    TasksReplicaRepository(test_db), TasksAuthHttpUserDirectory(client, "token")
                )
                await directory.get_many([envelope.aggregate_id])
