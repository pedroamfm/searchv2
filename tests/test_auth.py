import tempfile
from http.cookies import SimpleCookie
from pathlib import Path

import pytest
from fastapi import Request, Response

from app.auth import PASSWORD_HASHER, authenticate, create_admin, current_user, revoke_session
from app.auth_routes import login
from app.config import AppSettings
from app.database import database_connection
from app.errors import ApiError
from app.migrations import upgrade
from app.schemas import LoginRequest


def settings(root: Path) -> AppSettings:
    return AppSettings(_env_file=None, database_path=root / "data" / "radar.sqlite3", raw_root=root / "raw", reports_root=root / "reports", backups_root=root / "backups", login_max_failures=2)


def test_admin_login_session_lockout_and_revocation() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        configured = settings(Path(temporary))
        upgrade(configured, create_backup=False)
        with database_connection(configured.database_path, read_only=False) as connection:
            create_admin(connection, "admin@example.test", "Admin", "correct-password")
            stored = connection.execute("SELECT password_hash FROM app_users").fetchone()[0]
            assert stored != "correct-password" and PASSWORD_HASHER.verify(stored, "correct-password")
            for _ in range(2):
                with pytest.raises(ApiError):
                    authenticate(connection, configured, "admin@example.test", "incorrect-password")
            with pytest.raises(ApiError) as locked:
                authenticate(connection, configured, "admin@example.test", "correct-password")
            assert locked.value.status_code == 429
            connection.execute("UPDATE app_users SET locked_until_utc=NULL, failed_login_count=0")
            user, session_id, _ = authenticate(connection, configured, "admin@example.test", "correct-password")
            assert current_user(connection, session_id)["user_id"] == user["user_id"]
            revoke_session(connection, session_id)
            with pytest.raises(ApiError) as revoked:
                current_user(connection, session_id)
            assert revoked.value.code == "session_expired"


@pytest.mark.parametrize(
    ("origin_host", "secure"),
    [("radar.example.test", True), ("localhost:3000", False), ("192.0.2.10:3000", False)],
)
def test_proxy_login_cookies_support_https_and_local_access(tmp_path: Path, origin_host: str, secure: bool) -> None:
    configured = settings(tmp_path).model_copy(update={
        "environment": "production", "public_base_url": "https://radar.example.test",
    })
    upgrade(configured, create_backup=False)
    with database_connection(configured.database_path, read_only=False) as connection:
        create_admin(connection, "admin@example.test", "Admin", "correct-password")
    # Next.js supplies the browser host when proxying to the private API.
    request = Request({
        "type": "http", "method": "POST", "scheme": "http",
        "path": "/api/v1/auth/login", "query_string": b"",
        "headers": [(b"host", b"api:8000"), (b"x-forwarded-host", origin_host.encode())],
        "server": ("api", 8000),
    })
    response = Response()
    result = login(LoginRequest(email="admin@example.test", password="correct-password"), request, response, configured)
    assert result.email == "admin@example.test"
    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    assert all(("Secure" in cookie) is secure for cookie in cookies)
    assert "HttpOnly" in cookies[0]
    assert all("SameSite=lax" in cookie for cookie in cookies)
    parsed = SimpleCookie()
    parsed.load(cookies[0])
    with database_connection(configured.database_path) as connection:
        assert current_user(connection, parsed["product_radar_session"].value)["email"] == result.email
