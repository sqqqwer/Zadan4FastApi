import logging

from src.core.request_context import correlation_id_var


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds the correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add the correlation ID to the log record.

        Args:
            record: Log record to process.

        Returns:
            bool: Always True to keep the log record.
        """
        if not hasattr(record, "correlation_id"):
            record.correlation_id = correlation_id_var.get()
        return True
