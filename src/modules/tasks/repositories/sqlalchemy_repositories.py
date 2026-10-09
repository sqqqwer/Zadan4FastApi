from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task
from ..schemas import TaskCreateRepositoryScheme, TaskStatusScheme, TaskUpdateRepositoryScheme
from .abstracts import TaskAbstractRepository, TasksBaseRepository


class TasksModuleBaseSqlAlchemyRepository(TasksBaseRepository):
    """Base SQLAlchemy repository for the tasks module."""

    def __init__(self, session: AsyncSession, company_id: UUID):
        """Initialize the repository.

        Args:
            session: Database session used by the repository.
            company_id: Company ID.
        """
        super().__init__(company_id=company_id)
        self.session = session


class TaskSqlAlchemyRepository(TasksModuleBaseSqlAlchemyRepository, TaskAbstractRepository):
    """SQLAlchemy repository for task objects."""

    @override
    async def list_all(self, limit: int, offset: int) -> list[Task]:
        stmt = select(Task).where(Task.company_id == self.company_id).order_by(Task.id).offset(offset).limit(limit)
        tasks = await self.session.scalars(stmt)
        return list(tasks.all())

    @override
    async def retrieve(self, id: UUID) -> Task | None:
        stmt = select(Task).where(Task.id == id, Task.company_id == self.company_id)
        task = await self.session.execute(stmt)
        return task.scalar_one_or_none()

    @override
    async def retrieve_for_update(self, id: UUID) -> Task | None:
        stmt = select(Task).where(Task.id == id, Task.company_id == self.company_id).with_for_update(of=Task)
        task = await self.session.execute(stmt)
        return task.scalar_one_or_none()

    @override
    async def create(self, scheme: TaskCreateRepositoryScheme) -> Task:
        task = Task(**scheme.model_dump(), company_id=self.company_id)
        self.session.add(task)
        return task

    @override
    async def update(self, obj: Task, scheme: TaskUpdateRepositoryScheme) -> Task:
        for field, value in scheme.model_dump().items():
            setattr(obj, field, value)
        return obj

    @override
    async def delete(self, obj: Task) -> None:
        await self.session.delete(obj)

    @override
    async def update_status(self, task: Task, scheme: TaskStatusScheme) -> Task:
        task.status = scheme.status
        return task
