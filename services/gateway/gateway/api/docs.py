from typing import Any

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from ..utils.openapi import build_openapi

router = APIRouter(include_in_schema=False)


@router.get("/openapi.json")
async def openapi(request: Request) -> dict[str, Any]:
    """Build the gateway schema from the current upstream API contracts."""
    return await build_openapi(request.app)


@router.get("/docs")
async def swagger_ui(request: Request) -> HTMLResponse:
    """Display the gateway API grouped by microservice."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{request.app.title} - Swagger UI")


@router.get("/redoc")
async def redoc(request: Request) -> HTMLResponse:
    """Display the merged gateway API with ReDoc."""
    return get_redoc_html(openapi_url="/openapi.json", title=f"{request.app.title} - ReDoc")
