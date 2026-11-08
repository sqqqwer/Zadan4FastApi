from fastapi import APIRouter

from ..dependencies.metrics import MetricsServiceDependency
from ..schemas.heartbeat import HeartbeatRequest, HeartbeatResponse

router = APIRouter(tags=["heartbeat"])


@router.post("/heartbeat", responses={400: {"description": "Worker is not configured"}})
async def heartbeat(data: HeartbeatRequest, service: MetricsServiceDependency) -> HeartbeatResponse:
    """Store the latest progress timestamp of a configured worker."""
    return service.record_heartbeat(data)
