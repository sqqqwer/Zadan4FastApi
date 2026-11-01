from typing import Annotated

from fastapi import Depends, Query


class Pagination:
    """Pagination limit and offset."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        """Initialize the pagination limit and offset.

        Args:
            page: Page number starting from 1.
            size: Number of objects per page, from 1 to 100.
        """
        self.limit = size
        self.offset = (page - 1) * size


PaginationDependency = Annotated[Pagination, Depends(Pagination)]
