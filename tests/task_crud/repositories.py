from dataclasses import dataclass, field
from typing import override
from uuid import UUID, uuid4

from src.modules.tasks.models.task import Task
from src.modules.tasks.repositories.abstracts import TaskAbstractRepository, TasksBaseRepository
from src.modules.tasks.schemas import TaskCreateRepositoryScheme, TaskStatusScheme, TaskUpdateRepositoryScheme


@dataclass
class FakeDatabase:
    """In-memory storage for test objects."""

    tasks: dict[UUID, Task] = field(default_factory=dict)

class BaseMockRepository(TasksBaseRepository):
    """Base repository using the fake database."""

    def __init__(self, company_id: UUID, db: FakeDatabase):
        """Initialize the repository.

        Args:
            company_id: Company ID.
            db: Fake database used by the repository.
        """
        super().__init__(company_id=company_id)
        self.db = db

class TaskMockRepository(
    BaseMockRepository, TaskAbstractRepository
):
    """Test repository for account objects."""

    @override
    async def list_all(self, limit: int, offset: int) -> list[Task]:
        tasks = [
            task
            for task in self.db.tasks.values()
            if task.company_id == self.company_id
        ]

        tasks.sort(key=lambda task: task.id)

        return tasks[offset:offset + limit]

    @override
    async def retrieve(self, id: UUID) -> Task | None:
        task = self.db.tasks.get(id)

        if task is None or task.company_id != self.company_id:
            return None

        return task

    @override
    async def retrieve_for_update(self, id: UUID) -> Task | None:
        return await self.retrieve(id=id)

    @override
    async def create(self, scheme: TaskCreateRepositoryScheme) -> Task:
        task = Task(
            **scheme.model_dump(),
            id=uuid4(),
            company_id=self.company_id
        )
        self.db.tasks[task.id] = task
        return task

    @override
    async def update(self, obj: Task, scheme: TaskUpdateRepositoryScheme) -> Task:
        for task_field, scheme_value in scheme.model_dump().items():
            setattr(obj, task_field, scheme_value)
        return obj

    @override
    async def delete(self, obj: Task) -> None:
        del self.db.tasks[obj.id]

    @override
    async def update_status(self, task: Task, scheme: TaskStatusScheme) -> Task:
        task.status = scheme.status
        return task
