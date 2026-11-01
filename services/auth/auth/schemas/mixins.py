from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IdMixin(BaseModel):
    """Mixin scheme for id.

    Attributes:
        id: UUID
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID
