"""Shared FastAPI dependencies without router import cycles."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import Depends, Request

from app.auth import SESSION_COOKIE, current_user
from app.config import AppSettings, get_settings
from app.database import database_connection


def settings_dependency() -> AppSettings:
    return get_settings()


SettingsDependency = Annotated[AppSettings, Depends(settings_dependency)]


def user_dependency(request: Request, settings: SettingsDependency) -> dict[str, object]:
    session_id = request.cookies.get(SESSION_COOKIE)
    with database_connection(settings.database_path, read_only=False) as connection:
        user = current_user(connection, session_id)
        connection.execute("UPDATE user_sessions SET last_seen_at_utc=datetime('now') WHERE session_id=?", (hashlib.sha256((session_id or "").encode()).hexdigest(),))
        return dict(user)


CurrentUser = Annotated[dict[str, object], Depends(user_dependency)]
