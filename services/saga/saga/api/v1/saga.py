from fastapi import APIRouter

from ...config import get_settings
from ...dependencies.services import SagaServiceDependency
from ...schemas.saga import StalledSagasResponse

router = APIRouter(prefix="/saga/api/v1", tags=["saga"])


@router.get("/stalled")
async def get_stalled_sagas(service: SagaServiceDependency) -> StalledSagasResponse:
    """List unfinished sagas whose current step exceeded the configured timeout."""
    return await service.list_stalled(get_settings().saga_step_timeout_seconds)
