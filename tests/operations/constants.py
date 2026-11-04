from datetime import UTC, datetime
from uuid import UUID

from aiokafka import TopicPartition

EVENT_ID = UUID("ea694ed7-22bf-4b4b-a73d-288592b843a9")
CORRELATION_ID = UUID("6325f955-06c1-4b56-86ce-a90161c202b1")
EVENT_TYPE = "task.status_changed"
CREATED_AT = datetime(2026, 11, 4, tzinfo=UTC)
OUTBOX_TOTAL = 21
ATTEMPTS = 2
LAST_ERROR = "Kafka unavailable"

PARTITION_OFFSETS = {
    TopicPartition("auth.events", 0): (20, 100, 90),
    TopicPartition("tasks.events", 1): (0, 80, 60),
    TopicPartition("saga.events", 0): (5, 50, 50),
}
