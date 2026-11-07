from sqlalchemy import MetaData

from shared.base.models.models import BaseModelWithoutId


class NotificationBaseModelWithoutId(BaseModelWithoutId):
    """Base database model for the notification schema."""

    __abstract__ = True
    metadata = MetaData(schema="notification")
