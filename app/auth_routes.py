"""HTTP routes for local authentication."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response

from app.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    authenticate,
    current_user,
    require_csrf,
    revoke_session,
)
from app.database import database_connection
from app.config import AppSettings
from app.dependencies import SettingsDependency, user_dependency
from app.errors import ApiError
from app.schemas import LoginRequest, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def secure_cookie(request: Request, settings: AppSettings) -> bool:
    """Secure the public HTTPS session while keeping trusted local HTTP usable.

    Next.js overwrites X-Forwarded-Host with the original Host on every API
    rewrite. The API is private and reachable only through that proxy.
    """
    host = urlsplit("//" + request.headers.get("x-forwarded-host", request.headers.get("host", ""))).hostname
    public = urlsplit(settings.public_base_url)
    if public.scheme == "https" and host == public.hostname:
        return True
    if request.url.scheme == "https":
        return True
    if host == "localhost":
        return False
    try:
        if host and ip_address(host).is_private:
            return False
    except ValueError:
        pass
    return settings.environment == "production"


def audit(connection: object, request: Request, action: str, outcome: str, email: str | None = None) -> None:
    connection.execute("INSERT INTO audit_events (request_id, action_code, resource_type, resource_id, outcome, metadata_json, occurred_at_utc) VALUES (?, ?, 'session', ?, ?, '{}', datetime('now'))", (getattr(request.state, "request_id", None), action, email, outcome))  # type: ignore[attr-defined]


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, request: Request, response: Response, settings: SettingsDependency) -> UserResponse:
    with database_connection(settings.database_path, read_only=False) as connection:
        try:
            user, session_id, csrf = authenticate(connection, settings, str(payload.email), payload.password)
        except ApiError:
            audit(connection, request, "auth.login", "failed", str(payload.email))
            raise
        audit(connection, request, "auth.login", "succeeded", user["email"])
    secure = secure_cookie(request, settings)
    response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax", secure=secure, max_age=settings.session_hours * 3600, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="lax", secure=secure, max_age=settings.session_hours * 3600, path="/")
    return UserResponse(email=user["email"], display_name=user["display_name"], role=user["role"], csrf_token=csrf)


@router.get("/me", response_model=UserResponse)
def me(user: dict[str, object] = Depends(user_dependency)) -> UserResponse:  # noqa: B008
    return UserResponse(email=str(user["email"]), display_name=str(user["display_name"]), role=str(user["role"]))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, settings: SettingsDependency) -> Response:
    with database_connection(settings.database_path, read_only=False) as connection:
        user = current_user(connection, request.cookies.get(SESSION_COOKIE))
        require_csrf(user, request.headers.get("X-CSRF-Token"))
        revoke_session(connection, request.cookies.get(SESSION_COOKIE))
        audit(connection, request, "auth.logout", "succeeded", user["email"])
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = 204
    return response
