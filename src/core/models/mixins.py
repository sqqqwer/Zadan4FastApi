from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column


class IdPrimaryKeyMixin:
    """Mixin with a UUID primary key.

    Attributes:
        id: UUID
    """

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
