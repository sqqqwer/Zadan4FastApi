from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.events.onboarding import OnboardingCommand

from ..models.onboarding_task import OnboardingTask
from ..models.task import Task
from ..resources.enums import TaskStatusEnum
from ..services.constants import WELCOME_TASK_ESTIMATED_MINUTES, WELCOME_TASK_TITLE, WELCOME_TASK_TTL


class OnboardingRepository:
    """Store welcome task ownership and cancellation in the consumer's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Use the current message's session."""
        self.session = session

    async def get_or_create(self, command: OnboardingCommand) -> OnboardingTask:
        """Lock the saga marker, including when cancellation arrives before creation."""
        context = command.model_dump(mode="json")
        await self.session.execute(
            insert(OnboardingTask)
            .values(saga_id=command.saga_id, context=context, cancelled=False)
            .on_conflict_do_nothing(index_elements=[OnboardingTask.saga_id])
        )
        record = await self.session.scalar(
            select(OnboardingTask).where(OnboardingTask.saga_id == command.saga_id).with_for_update()
        )
        if record is None:
            raise RuntimeError("Tasks onboarding record disappeared")
        if record.context != context:
            raise ValueError("Tasks onboarding command changed identifiers for an existing saga")
        return record

    async def create_task(self, record: OnboardingTask, command: OnboardingCommand) -> None:
        """Create one welcome task owned by this saga without requiring a user replica."""
        record.task_id = uuid4()
        self.session.add(
            Task(
                id=record.task_id,
                company_id=command.company_id,
                title=WELCOME_TASK_TITLE,
                description="Познакомьтесь с компанией и своим подразделением.",
                deadline=datetime.now(UTC) + WELCOME_TASK_TTL,
                status=TaskStatusEnum.CREATED,
                status_version=0,
                estimated_minutes=WELCOME_TASK_ESTIMATED_MINUTES,
                author_id=command.user_id,
                responsible_id=command.user_id,
                observer_ids=[],
                executor_ids=[command.user_id],
            )
        )

    async def cancel_task(self, record: OnboardingTask) -> tuple[Task, TaskStatusEnum] | None:
        """Cancel an existing owned task once and retain the marker if no task exists."""
        record.cancelled = True
        if record.task_id is None:
            return None
        task = await self.session.scalar(
            select(Task)
            .where(Task.id == record.task_id, Task.company_id == UUID(record.context["company_id"]))
            .with_for_update()
        )
        if task is None or task.status == TaskStatusEnum.CANCELED:
            return None
        old_status = task.status
        task.status = TaskStatusEnum.CANCELED
        task.status_version += 1
        return task, old_status
