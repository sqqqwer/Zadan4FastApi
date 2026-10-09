from abc import abstractmethod
from uuid import UUID

from src.core.repositories.base import BaseRepository
from src.core.repositories.crud import CrudAbstractRepository

from ..models.task import Task
from ..schemas import TaskCreateRepositoryScheme, TaskStatusScheme, TaskUpdateRepositoryScheme


class TasksBaseRepository(BaseRepository):
    """Base repository for the tasks module."""

    def __init__(self, company_id: UUID):
        """Initialize the repository.

        Args:
            company_id: Company ID.
        """
        self.company_id = company_id


class TaskAbstractRepository(
    TasksBaseRepository, CrudAbstractRepository[Task, TaskCreateRepositoryScheme, TaskUpdateRepositoryScheme]
):
    """Abstract repository for task objects."""

    @abstractmethod
    async def list_all(self, limit: int, offset: int) -> list[Task]:
        """Get a list of tasks.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            list[Task]: List of tasks.
        """
        ...

    @abstractmethod
    async def retrieve(self, id: UUID) -> Task | None:
        """Get the task by ID.

        Args:
            id: Task ID.

        Returns:
            Task: Task object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def retrieve_for_update(self, id: UUID) -> Task | None:
        """Get the task by ID and lock it for update.

        Args:
            id: Task ID.

        Returns:
            Task: Task object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create(self, scheme: TaskCreateRepositoryScheme) -> Task:
        """Create the task.

        Args:
            scheme: Task data used by the operation.

        Returns:
            Task: Task object.
        """
        ...

    @abstractmethod
    async def update(self, obj: Task, scheme: TaskUpdateRepositoryScheme) -> Task:
        """Update the task.

        Args:
            obj: Database object to change.
            scheme: Task data used by the operation.

        Returns:
            Task: Task object.
        """
        ...

    @abstractmethod
    async def delete(self, obj: Task) -> None:
        """Delete the task.

        Args:
            obj: Database object to change.
        """
        ...

    @abstractmethod
    async def update_status(self, task: Task, scheme: TaskStatusScheme) -> Task:
        """Update the task status.

        Args:
            task: Task object.
            scheme: New task status.

        Returns:
            Task: Task object.
        """
        ...
