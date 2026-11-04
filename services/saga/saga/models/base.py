from sqlalchemy import MetaData

from shared.base.models.models import BaseModelWithoutId


class SagaBaseModelWithoutId(BaseModelWithoutId):
    """Base database model for the saga service's own schema."""

    __abstract__ = True
    metadata = MetaData(schema="saga")
