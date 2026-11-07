from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from ..dependencies.metrics import MetricsServiceDependency

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=Response)
async def metrics(service: MetricsServiceDependency) -> Response:
    """Collect upstream metrics and expose them in Prometheus format."""
    return Response(
        content=await service.collect(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
