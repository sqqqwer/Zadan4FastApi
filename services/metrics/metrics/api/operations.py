from fastapi import APIRouter

router = APIRouter(tags=["operations"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Check HTTP liveness independently of upstream services."""
    return {"status": "ok"}
