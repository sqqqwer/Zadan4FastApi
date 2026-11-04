import asyncio
import logging
from typing import Literal

from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.admin import AIOKafkaAdminClient

from .abstracts import OperationsAbstractRepository
from .schemas import (
    ConsumerLagResponse,
    ConsumerPartitionLag,
    PendingOutboxMessage,
    PendingOutboxResponse,
    ReadinessResponse,
)

logger = logging.getLogger(__name__)
READINESS_TIMEOUT_SECONDS = 3


class OperationsService:
    """Readiness checks and outbox diagnostics for one HTTP service."""

    def __init__(
        self,
        repository: OperationsAbstractRepository,
        kafka_bootstrap_servers: str,
        consumer_name: str,
        *,
        consumer_topics: tuple[str, ...] = ("auth.events", "org.events", "tasks.events", "saga.events"),
    ):
        """Initialize the service with its database repository and Kafka address."""
        self.repository = repository
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.consumer_name = consumer_name
        self.consumer_topics = consumer_topics

    async def check_database(self) -> Literal["ok", "error"]:
        """Check database availability within the readiness timeout."""
        try:
            async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
                await self.repository.check_connection()
        except Exception:
            logger.exception("Readiness check failed: database")
            await self.repository.rollback()
            return "error"
        return "ok"

    async def check_kafka(self) -> Literal["ok", "error"]:
        """Request cluster metadata and always close the probe's connection."""
        client = AIOKafkaAdminClient(
            bootstrap_servers=self.kafka_bootstrap_servers,
            request_timeout_ms=READINESS_TIMEOUT_SECONDS * 1000,
        )
        try:
            try:
                async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
                    await client.start()
                    await client.describe_cluster()
            finally:
                await client.close()
        except Exception:
            logger.exception("Readiness check failed: kafka")
            return "error"
        return "ok"

    async def ready(self) -> ReadinessResponse:
        """Check the database and Kafka independently and in parallel."""
        database, kafka = await asyncio.gather(self.check_database(), self.check_kafka())
        return ReadinessResponse(
            status="ready" if database == kafka == "ok" else "not_ready",
            database=database,
            kafka=kafka,
        )

    async def list_pending_outbox(self, limit: int, offset: int) -> PendingOutboxResponse:
        """Build a page of publication diagnostics and log the total count."""
        total = await self.repository.count_pending_outbox()
        messages = await self.repository.list_pending_outbox(limit=limit, offset=offset)
        logger.info("Outbox pending: count=%s", total)
        return PendingOutboxResponse(
            total=total,
            items=[PendingOutboxMessage.model_validate(message) for message in messages],
        )

    async def consumer_lag(self) -> ConsumerLagResponse:
        """Read group offsets without joining the group or consuming messages."""
        admin = AIOKafkaAdminClient(
            bootstrap_servers=self.kafka_bootstrap_servers,
            request_timeout_ms=READINESS_TIMEOUT_SECONDS * 1000,
        )
        reader = AIOKafkaConsumer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=None,
            enable_auto_commit=False,
            request_timeout_ms=READINESS_TIMEOUT_SECONDS * 1000,
        )
        try:
            try:
                async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
                    await admin.start()
                    await reader.start()
                    partitions = await self._read_partition_lags(admin, reader)
            finally:
                await asyncio.gather(admin.close(), reader.stop())
        except Exception:
            logger.exception("Consumer lag check failed: group_id=%s", self.consumer_name)
            return ConsumerLagResponse(status="error", group_id=self.consumer_name, total_lag=None, partitions=[])
        total_lag = sum(partition.lag for partition in partitions)
        logger.info("Consumer lag: group_id=%s total_lag=%s", self.consumer_name, total_lag)
        return ConsumerLagResponse(
            status="ok", group_id=self.consumer_name, total_lag=total_lag, partitions=partitions
        )

    async def _read_partition_lags(
        self, admin: AIOKafkaAdminClient, reader: AIOKafkaConsumer
    ) -> list[ConsumerPartitionLag]:
        """Measure the existing partitions of this consumer's subscribed topics."""
        partitions = [
            TopicPartition(topic, partition)
            for topic in self.consumer_topics
            for partition in sorted(reader.partitions_for_topic(topic) or ())
        ]
        if not partitions:
            return []
        committed, beginnings, ends = await asyncio.gather(
            admin.list_consumer_group_offsets(self.consumer_name, partitions=partitions),
            reader.beginning_offsets(partitions),
            reader.end_offsets(partitions),
        )
        result = []
        for partition in partitions:
            offset = committed[partition].offset if partition in committed else -1
            committed_offset = offset if offset >= 0 else None
            beginning, end = beginnings[partition], ends[partition]
            effective_offset = offset if beginning <= offset <= end else beginning
            result.append(
                ConsumerPartitionLag(
                    topic=partition.topic,
                    partition=partition.partition,
                    committed_offset=committed_offset,
                    beginning_offset=beginning,
                    end_offset=end,
                    lag=end - effective_offset,
                )
            )
        return result
