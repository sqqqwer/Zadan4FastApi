from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class IdempotencyCreateRepositoryScheme(BaseModel):
    """Data for creating an idempotency record.

    Attributes:
        scope: str
        key: UUID
        request_hash: str
        status_code: int
        response_body: dict[str, Any]
        created_at: datetime
    """

    scope: str
    key: UUID
    request_hash: str
    status_code: int
    response_body: dict[str, Any]
    created_at: datetime
