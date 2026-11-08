import asyncio
import logging

from httpx import AsyncClient, HTTPError
from prometheus_client import CollectorRegistry, Gauge, generate_latest

from shared.operations.schemas import ConsumerLagResponse, PendingOutboxResponse

from ..resources.exceptions import HeartbeatWorkerNotConfigured
from ..schemas.heartbeat import HeartbeatRequest, HeartbeatResponse, WorkerRole

logger = logging.getLogger(__name__)


class MetricsService:
    """Collect operational metrics without accessing other services' databases."""

    def __init__(
        self,
        client: AsyncClient,
        service_urls: dict[str, str],
        max_concurrency: int,
        workers: dict[str, list[WorkerRole]],
    ) -> None:
        """Initialize upstream connections and the concurrent request limit."""
        self.client = client
        self.service_urls = service_urls
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.heartbeats: dict[tuple[str, WorkerRole], float | None] = {
            (service, role): None for service, roles in workers.items() for role in roles
        }

    def record_heartbeat(self, data: HeartbeatRequest) -> HeartbeatResponse:
        """Keep the latest progress timestamp without moving it backwards."""
        key = (data.service, data.role)
        if key not in self.heartbeats:
            raise HeartbeatWorkerNotConfigured
        timestamp = max(self.heartbeats[key] or 0, data.last_progress_timestamp)
        self.heartbeats[key] = timestamp
        return HeartbeatResponse(
            service=data.service,
            role=data.role,
            last_progress_timestamp=timestamp,
        )

    async def collect(self) -> bytes:
        """Build a fresh metrics snapshot, omitting unavailable measurements."""
        registry = CollectorRegistry()
        outbox_size = Gauge(
            "outbox_pending_messages",
            "Number of outbox messages awaiting publication",
            labelnames=["service"],
            registry=registry,
        )
        consumer_lag = Gauge(
            "consumer_lag_messages",
            "Consumer group lag measured in messages",
            labelnames=["service", "group_id"],
            registry=registry,
        )
        scrape_success = Gauge(
            "metrics_scrape_success",
            "Whether the upstream operation was collected successfully",
            labelnames=["service", "operation"],
            registry=registry,
        )
        results = await asyncio.gather(
            *(self._collect_service(service, base_url) for service, base_url in self.service_urls.items())
        )
        for service, outbox, lag in results:
            scrape_success.labels(service=service, operation="outbox").set(outbox is not None)
            scrape_success.labels(service=service, operation="consumer-lag").set(lag is not None)
            if outbox is not None:
                outbox_size.labels(service=service).set(outbox)
            if lag is not None and lag.total_lag is not None:
                consumer_lag.labels(service=service, group_id=lag.group_id).set(lag.total_lag)

        self._collect_heartbeats(registry)

        return generate_latest(registry)

    def _collect_heartbeats(self, registry: CollectorRegistry) -> None:
        """Expose reported progress and distinguish workers without a heartbeat."""
        heartbeat_received = Gauge(
            "worker_heartbeat_received",
            "Whether a heartbeat has been received since the exporter started",
            labelnames=["service", "role"],
            registry=registry,
        )
        last_progress = Gauge(
            "worker_last_progress_timestamp_seconds",
            "Unix timestamp of the last reported worker progress",
            labelnames=["service", "role"],
            registry=registry,
        )
        for (service, role), timestamp in self.heartbeats.items():
            heartbeat_received.labels(service=service, role=role).set(timestamp is not None)
            if timestamp is not None:
                last_progress.labels(service=service, role=role).set(timestamp)

    async def _collect_service(
        self, service: str, base_url: str
    ) -> tuple[str, int | None, ConsumerLagResponse | None]:
        """Collect outbox size and consumer lag independently."""
        outbox, lag = await asyncio.gather(
            self._read_outbox(service, base_url),
            self._read_consumer_lag(service, base_url),
        )
        return service, outbox, lag

    async def _read_outbox(self, service: str, base_url: str) -> int | None:
        """Read the pending count while requesting only one diagnostic record."""
        try:
            async with self.semaphore:
                response = await self.client.get(f"{base_url.rstrip('/')}/outbox", params={"page": 1, "size": 1})
                response.raise_for_status()
            result = PendingOutboxResponse.model_validate(response.json())
            if result.total < 0:
                raise ValueError("Pending outbox count must not be negative")
        except (HTTPError, ValueError) as error:
            logger.warning("Outbox metrics collection failed: service=%s error=%s", service, error)
            return None
        return result.total

    async def _read_consumer_lag(self, service: str, base_url: str) -> ConsumerLagResponse | None:
        """Read group lag without treating failed measurements as zero."""
        try:
            async with self.semaphore:
                response = await self.client.get(f"{base_url.rstrip('/')}/consumer-lag")
                response.raise_for_status()
            result = ConsumerLagResponse.model_validate(response.json())
            if result.status != "ok" or result.total_lag is None or result.total_lag < 0:
                raise ValueError("Consumer lag measurement is unavailable or invalid")
        except (HTTPError, ValueError) as error:
            logger.warning("Consumer lag metrics collection failed: service=%s error=%s", service, error)
            return None
        return result
