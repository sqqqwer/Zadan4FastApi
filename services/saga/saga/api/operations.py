from fastapi import APIRouter, Response, status

from shared.operations.schemas import ConsumerLagResponse, PendingOutboxResponse, ReadinessResponse
from shared.pagination.dependencies import PaginationDependency

from ..dependencies.operations import OperationsServiceDependency

router = APIRouter(tags=["operations"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Check HTTP liveness independently of the database and Kafka."""
    return {"status": "ok"}


@router.get("/ready", responses={503: {"model": ReadinessResponse}})
async def ready(response: Response, service: OperationsServiceDependency) -> ReadinessResponse:
    """Return 503 if either dependency is unavailable or times out."""
    result = await service.ready()
    if result.status == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/outbox")
async def pending_outbox(
    pagination: PaginationDependency,
    service: OperationsServiceDependency,
) -> PendingOutboxResponse:
    """List unpublished messages, oldest first, and log their total count."""
    return await service.list_pending_outbox(limit=pagination.limit, offset=pagination.offset)


@router.get("/consumer-lag", responses={503: {"model": ConsumerLagResponse}})
async def consumer_lag(response: Response, service: OperationsServiceDependency) -> ConsumerLagResponse:
    """Get the lag of this service's consumer group without changing its offsets."""
    result = await service.consumer_lag()
    if result.status == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
