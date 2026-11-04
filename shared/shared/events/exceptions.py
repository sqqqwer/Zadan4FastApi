from aiokafka.errors import KafkaError, KafkaTimeoutError
from httpx import TransportError
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as DatabaseTimeoutError


class FatalEventError(ValueError):
    """The message cannot be processed without correcting its contents."""


class TransientEventError(Exception):
    """The handler can be retried after a temporary dependency failure."""


def is_transient_error(error: Exception) -> bool:
    """Identify connection failures, database contention and retriable broker errors."""
    if isinstance(error, (TransientEventError, OSError, TransportError, DatabaseTimeoutError, KafkaTimeoutError)):
        return True
    if isinstance(error, KafkaError):
        return bool(error.retriable)

    original = error.orig if isinstance(error, DBAPIError) else error
    sqlstate = getattr(original, "sqlstate", None)
    if sqlstate is not None:
        return sqlstate.startswith(("08", "40", "53")) or sqlstate in ("55P03", "57P01", "57P02", "57P03")
    return isinstance(error, DBAPIError) and (error.connection_invalidated or isinstance(error, OperationalError))
