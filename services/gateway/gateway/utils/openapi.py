from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.openapi.utils import get_openapi
from httpx import AsyncClient, HTTPError

from ..constants.http import PROXY_METHODS
from ..constants.operations import OPERATION_PATHS


def rewrite_references(value: Any, references: dict[str, str]) -> None:
    """Rewrite the local schema references used by the upstream APIs."""
    if isinstance(value, dict):
        if "discriminator" in value:
            raise ValueError("Unsupported OpenAPI discriminator")
        for key, item in value.items():
            if key == "$ref":
                value[key] = references[item]
            else:
                rewrite_references(item, references)
    elif isinstance(value, list):
        for item in value:
            rewrite_references(item, references)


def merge_service_schema(schema: dict[str, Any], upstream: dict[str, Any], service: str) -> None:
    """Merge the schemas and operations exposed by the existing services."""
    components = upstream.get("components", {})

    if components.get("securitySchemes", {}) not in ({}, schema["components"]["securitySchemes"]):
        raise ValueError("Unsupported OpenAPI security schemes")
    if upstream.get("security"):
        raise ValueError("Unsupported root OpenAPI security")

    definitions = components.get("schemas", {})
    references = {f"#/components/schemas/{name}": f"#/components/schemas/{service}_{name}" for name in definitions}

    rewrite_references(upstream, references)

    target = schema["components"].setdefault("schemas", {})
    for name, definition in definitions.items():
        target[f"{service}_{name}"] = definition

    prefix = f"/{service}/api/v1"
    aliases = {
        upstream_path: f"/{service}/operations/{operation}"
        for operation, upstream_path in OPERATION_PATHS[service].items()
    }

    for path, path_item in upstream["paths"].items():
        alias = aliases.get(path)
        is_business_path = service != "saga" and (path == prefix or path.startswith(f"{prefix}/"))

        if alias is None and not is_business_path:
            continue

        for method, operation in path_item.items():
            if method.upper() not in PROXY_METHODS or "servers" in operation or "callbacks" in operation:
                raise ValueError("Unsupported OpenAPI operation")
            if alias is not None and method != "get":
                raise ValueError("Unsupported operational HTTP method")
            if operation.get("security", []) not in ([], [{"HTTPBearer": []}]):
                raise ValueError("Unsupported operation security")

            operation["tags"] = [service]
            operation["operationId"] = f"{service}_{operation['operationId']}"

            if alias is not None:
                operation["security"] = []

        schema["paths"][alias or path] = path_item


async def build_openapi(app: FastAPI) -> dict[str, Any]:
    """Load current upstream schemas and combine their public contracts."""
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        routes=app.routes,
        tags=[{"name": service} for service in app.state.upstream_urls] + [{"name": "operations"}],
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
    }
    client: AsyncClient = app.state.upstream_http_client
    for service, base_url in app.state.upstream_urls.items():
        try:
            response = await client.get(f"{base_url.rstrip('/')}/openapi.json")
            response.raise_for_status()
            upstream = response.json()
            merge_service_schema(schema, upstream, service)
        except (HTTPError, ValueError, TypeError, KeyError, AttributeError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to load {service} OpenAPI schema",
            ) from error
    return schema
