from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DeadLetterMessage(BaseModel):
    """Preserve a rejected message and the consumer's failure details."""

    source_topic: str
    partition: int
    offset: int
    consumer_name: str
    original_message: str | None
    original_encoding: Literal["utf-8", "base64"]
    reason: str
    error_type: str
    attempts: int
    correlation_id: UUID | None
    failed_at: datetime
