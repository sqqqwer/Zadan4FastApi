from typing import Annotated

from fastapi import Depends, Request

from ..services.metrics_service import MetricsService


def get_metrics_service(request: Request) -> MetricsService:
    """Get the metrics service bound to the application's HTTP client."""
    return request.app.state.metrics_service


MetricsServiceDependency = Annotated[MetricsService, Depends(get_metrics_service)]
