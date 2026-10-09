import logging.config


def setup_logging(level: str = "INFO") -> None:
    """Set up console and file logging.

    Args:
        level: Console logging level.
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "filters": {"correlation_id": {"()": "src.core.logging.filters.CorrelationIdFilter"}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                    "filters": ["correlation_id"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": "tasks-platform.log",
                    "maxBytes": 5_000_000,
                    "backupCount": 3,
                    "encoding": "utf-8",
                    "level": "DEBUG",
                    "filters": ["correlation_id"],
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
            },
            "loggers": {
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )
