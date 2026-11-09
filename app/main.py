"""FastAPI entrypoint for Product Radar."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.auth_routes import router as auth_router
from app.config import get_settings
from app.errors import ApiError, api_error_handler
from app.health import readiness
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    for directory in settings.required_directories():
        directory.mkdir(parents=True, exist_ok=True)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    docs_url="/api/docs" if settings.environment != "production" else None,
    openapi_url="/api/openapi.json" if settings.environment != "production" else None,
    lifespan=lifespan,
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.include_router(auth_router)
app.include_router(router)


@app.middleware("http")
async def request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    # Keep authenticated files and API data out of the public proxy cache,
    # including report URLs ending in normally cacheable extensions like .pdf.
    if request.url.path.startswith("/api/v1/") and not request.url.path.startswith("/api/v1/health/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.get("/api/v1/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "ok", "service": "api", "version": __version__}


@app.get("/api/v1/health/ready", tags=["health"])
def ready(response: Response) -> dict[str, object]:
    is_ready, checks = readiness(settings)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if is_ready else "not_ready",
        "service": "api",
        "version": __version__,
        "checks": checks,
    }
