"""Local password, session, CSRF and authorization services."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import cast

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import AppSettings
from app.errors import ApiError

PASSWORD_HASHER = PasswordHasher()
SESSION_COOKIE = "product_radar_session"
CSRF_COOKIE = "product_radar_csrf"


def now() -> datetime:
    return datetime.now(UTC)


def timestamp(value: datetime | None = None) -> str:
    return (value or now()).isoformat()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_admin(connection: sqlite3.Connection, email: str, display_name: str, password: str) -> None:
    instant = timestamp()
    connection.execute(
        """INSERT INTO app_users (email, display_name, role, password_hash, created_at_utc, updated_at_utc)
        VALUES (?, ?, 'admin', ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET display_name=excluded.display_name, role='admin',
        password_hash=excluded.password_hash, is_active=1, failed_login_count=0, locked_until_utc=NULL,
        updated_at_utc=excluded.updated_at_utc""",
        (email.lower(), display_name, PASSWORD_HASHER.hash(password), instant, instant),
    )


def authenticate(connection: sqlite3.Connection, settings: AppSettings, email: str, password: str) -> tuple[sqlite3.Row, str, str]:
    user = connection.execute("SELECT * FROM app_users WHERE email = ?", (email.lower(),)).fetchone()
    invalid = ApiError(401, "invalid_credentials", "Credenciales inválidas.")
    if user is None or not user["is_active"]:
        raise invalid
    locked = user["locked_until_utc"]
    if locked and datetime.fromisoformat(locked) > now():
        raise ApiError(429, "invalid_credentials", "La cuenta está temporalmente bloqueada.")
    try:
        valid: bool = PASSWORD_HASHER.verify(user["password_hash"], password)
    except (InvalidHashError, VerificationError):
        valid = False
    if not valid:
        failures = int(user["failed_login_count"]) + 1
        lock = now() + timedelta(minutes=settings.login_lock_minutes) if failures >= settings.login_max_failures else None
        connection.execute("UPDATE app_users SET failed_login_count=?, locked_until_utc=?, updated_at_utc=? WHERE user_id=?", (failures, timestamp(lock) if lock else None, timestamp(), user["user_id"]))
        raise invalid
    connection.execute("UPDATE app_users SET failed_login_count=0, locked_until_utc=NULL, updated_at_utc=? WHERE user_id=?", (timestamp(), user["user_id"]))
    session_id, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = now() + timedelta(hours=settings.session_hours)
    connection.execute("INSERT INTO user_sessions (session_id, user_id, csrf_token_hash, created_at_utc, expires_at_utc, last_seen_at_utc) VALUES (?, ?, ?, ?, ?, ?)", (token_hash(session_id), user["user_id"], token_hash(csrf), timestamp(), timestamp(expiry), timestamp()))
    return user, session_id, csrf


def current_user(connection: sqlite3.Connection, session_id: str | None) -> sqlite3.Row:
    if not session_id:
        raise ApiError(401, "authentication_required", "Debes iniciar sesión.")
    row = connection.execute("""SELECT u.*, s.csrf_token_hash, s.expires_at_utc, s.revoked_at_utc FROM user_sessions s JOIN app_users u ON u.user_id=s.user_id WHERE s.session_id=?""", (token_hash(session_id),)).fetchone()
    if row is None or row["revoked_at_utc"] or datetime.fromisoformat(row["expires_at_utc"]) <= now() or not row["is_active"]:
        raise ApiError(401, "session_expired", "La sesión expiró. Inicia sesión nuevamente.")
    return cast(sqlite3.Row, row)


def require_csrf(user: sqlite3.Row, supplied: str | None) -> None:
    if not supplied or not secrets.compare_digest(token_hash(supplied), user["csrf_token_hash"]):
        raise ApiError(403, "csrf_failed", "No se pudo validar la solicitud.")


def revoke_session(connection: sqlite3.Connection, session_id: str | None) -> None:
    if session_id:
        connection.execute("UPDATE user_sessions SET revoked_at_utc=? WHERE session_id=?", (timestamp(), token_hash(session_id)))
