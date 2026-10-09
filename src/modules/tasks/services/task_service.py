import datetime
import logging
from typing import override
from uuid import UUID, uuid4

from src.core.events.bus import AbstractEventsBus
from src.core.events.envelope import EventEnvelope
from src.core.events.types import EventType
from src.core.request_context import correlation_id_var
from src.core.resources.exceptions import NotFoundError
from src.core.services.crud import CrudAbstractService
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract

from ..ports import UserDirectory
from ..repositories.abstracts import TaskAbstractRepository
from ..resources.enums import TaskStatusEnum
from ..resources.exceptions import (
    InvalidTaskStatusTransition,
    TaskNewStatusMatchesCurrentStatus,
    TaskNotFound,
    UserFromDifferentCompany,
    UserNotFound,
)
from ..schemas import (
    TaskCreatePayloadScheme,
    TaskCreateRepositoryScheme,
    TaskResponseScheme,
    TaskStatusScheme,
    TaskUpdateRepositoryScheme,
)
from .constants import EVENT_PRODUCER
from .status_transitions import ALLOWED_STATUS_TRANSITIONS

logger = logging.getLogger(__name__)


class TaskService(CrudAbstractService[TaskCreatePayloadScheme, TaskCreatePayloadScheme, TaskResponseScheme]):
    """Task service."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        crud_repository: TaskAbstractRepository,
        uow: UowAbstract,
        current_user_id: UUID,
        company_id: UUID,
        user_directory: UserDirectory,
        event_bus: AbstractEventsBus,
    ):
        """Initialize the service.

        Args:
            crud_repository: Repository for CRUD operations.
            uow: Unit of work for database operations.
            current_user_id: Current user ID.
            company_id: Company ID.
            user_directory: User directory used to get user data.
            event_bus: Event bus used to publish events.
        """
        super().__init__(
            crud_repository=crud_repository,
            response_scheme=TaskResponseScheme,
            uow=uow,
            current_user_id=current_user_id,
            company_id=company_id,
        )
        self.task_repository = crud_repository
        self.user_directory = user_directory
        self.event_bus = event_bus

    async def create(
        self, payload: TaskCreatePayloadScheme, idempotency: IdempotencyAbstractService
    ) -> TaskResponseScheme:
        """Create the task.

        Args:
            payload: Task data used by the operation.
            idempotency: Service for checking and saving idempotent operations.

        Returns:
            TaskResponseScheme: Task response data.

        Raises:
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            UserFromDifferentCompany: If the user belongs to a different company.
            UserNotFound: If the user is not found.
        """
        idempotency_record = await idempotency.check_operation(
            f"{self._get_model_name()}.create:v1:{self.company_id}:{self.current_user_id}"
        )
        if idempotency_record is not None:
            return self.response_scheme.model_validate(idempotency_record)

        list_of_users = list(
            {
                self.current_user_id,
                payload.responsible_id,
                *payload.observer_ids,
                *payload.executor_ids,
            }
        )

        users = await self.user_directory.get_many(list_of_users)

        if len(list_of_users) > len(users):
            raise UserNotFound()

        for user in users.values():
            if user.company_id != self.company_id:
                raise UserFromDifferentCompany()

        create_scheme = TaskCreateRepositoryScheme(
            status=TaskStatusEnum.CREATED,
            author_id=self.current_user_id,
            **payload.model_dump(exclude_unset=True),
        )

        obj = await self.crud_repository.create(scheme=create_scheme)

        await self.uow.flush()
        response = self.response_scheme.model_validate(obj)

        await idempotency.save_operation(
            response_json=response.model_dump(
                mode="json",
                by_alias=True,
            )
        )

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} created: id={response.id}.")

        return response

    async def update(self, id: UUID, payload: TaskCreatePayloadScheme) -> TaskResponseScheme:
        """Update the task.

        Args:
            id: Task ID.
            payload: Task data used by the operation.

        Returns:
            TaskResponseScheme: Task response data.

        Raises:
            TaskNotFound: If the task is not found.
            UserFromDifferentCompany: If the user belongs to a different company.
            UserNotFound: If the user is not found.
        """
        obj = await self.task_repository.retrieve_for_update(id=id)

        if obj is None:
            raise self._not_found_exception()

        list_of_users = list(
            {
                obj.author_id,
                payload.responsible_id,
                *payload.observer_ids,
                *payload.executor_ids,
            }
        )

        users = await self.user_directory.get_many(list_of_users)

        if len(list_of_users) > len(users):
            raise UserNotFound()

        for user in users.values():
            if user.company_id != self.company_id:
                raise UserFromDifferentCompany()

        update_scheme = TaskUpdateRepositoryScheme(**payload.model_dump())

        await self.task_repository.update(obj=obj, scheme=update_scheme)
        response = self.response_scheme.model_validate(obj)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} updated: id={response.id}.")
        return response

    async def change_state(self, id: UUID, payload: TaskStatusScheme) -> TaskResponseScheme:
        """Change the task status.

        Args:
            id: Task ID.
            payload: New task status.

        Returns:
            TaskResponseScheme: Task response data.

        Raises:
            InvalidTaskStatusTransition: If the requested task status transition is not allowed.
            TaskNewStatusMatchesCurrentStatus: If the task already has the requested status.
            TaskNotFound: If the task is not found.
            TaskStatusUnsupportable: If no transition rules exist for the current task status.
        """
        task = await self.task_repository.retrieve_for_update(id=id)
        if task is None:
            raise self._not_found_exception()

        current_status_rules = ALLOWED_STATUS_TRANSITIONS.get(task.status, None)
        if current_status_rules is None:
            raise InvalidTaskStatusTransition()
        if task.status == payload.status:
            raise TaskNewStatusMatchesCurrentStatus()
        if payload.status not in current_status_rules:
            raise InvalidTaskStatusTransition()

        old_status = task.status.value
        task = await self.task_repository.update_status(task=task, scheme=payload)

        response = self.response_scheme.model_validate(task)

        await self.uow.commit()

        logger.info(
            f"{self._get_model_name()} change state: id={response.id}"
            f" old_status={old_status} new_status={payload.status}."
        )

        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=EventType.TASK_STATUS_CHANGED,
            aggregate_id=task.id,
            occurred_at=datetime.datetime.now(datetime.UTC),
            schema_version=1,
            correlation_id=UUID(correlation_id_var.get()),
            causation_id=None,
            producer=EVENT_PRODUCER,
            payload={
                "task_id": task.id,
                "task_author_id": task.author_id,
                "user_changed_state_id": self.current_user_id,
                "old_status": old_status,
                "new_status": task.status.value,
            },
        )
        logger.info("task.status_changed Event start publish.")
        await self.event_bus.publish(envelope)

        return response

    @override
    def _get_model_name(self) -> str:
        return "task"

    @override
    def _not_found_exception(self) -> NotFoundError:
        return TaskNotFound()
