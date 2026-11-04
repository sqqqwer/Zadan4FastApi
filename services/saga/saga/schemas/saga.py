from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EmployeeRegisteredPayload(BaseModel):
    """Registration data required to start employee onboarding."""

    user_id: UUID
    company_id: UUID
    invite_id: UUID
    position_id: UUID
    struct_id: UUID


class SagaResultPayload(BaseModel):
    """Common payload of a participant's successful reply."""

    saga_id: UUID


class SagaFailurePayload(SagaResultPayload):
    """A business refusal that starts compensation instead of a retry."""

    reason: str = Field(min_length=1, max_length=1024)


class SagaCreateScheme(BaseModel):
    """Scenario-independent data used to insert initial saga state."""

    saga_type: str = Field(min_length=1)
    business_key: str = Field(min_length=1)
    step: str = Field(min_length=1)
    context: dict[str, Any]
