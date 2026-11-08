import time
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WorkerRole = Literal["consumer", "publisher"]
MAX_HEARTBEAT_CLOCK_SKEW_SECONDS = 5


class HeartbeatRequest(BaseModel):
    """Last progress timestamp reported by one configured worker."""

    service: str = Field(min_length=1, max_length=64)
    role: WorkerRole
    last_progress_timestamp: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("last_progress_timestamp")
    @classmethod
    def validate_last_progress_timestamp(cls, value: float) -> float:
        """Reject timestamps beyond the allowed worker clock difference."""
        if value > time.time() + MAX_HEARTBEAT_CLOCK_SKEW_SECONDS:
            raise ValueError("Heartbeat timestamp is too far in the future")
        return value


class HeartbeatResponse(HeartbeatRequest):
    """Latest stored progress timestamp after accepting a heartbeat."""

    status: Literal["ok"] = "ok"
