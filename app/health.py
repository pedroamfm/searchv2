"""Readiness checks that do not mutate Product Radar data."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.config import AppSettings
from app.migrations import current_revision, expected_revision


def directory_status(path: Path) -> dict[str, Any]:
    return {
        "exists": path.is_dir(),
        "path": str(path),
    }


def database_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "readable": False}

    try:
        connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        try:
            connection.execute("SELECT 1").fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return {"exists": True, "readable": False}

    return {"exists": True, "readable": True}


def readiness(settings: AppSettings) -> tuple[bool, dict[str, Any]]:
    directories = {
        "raw": directory_status(settings.raw_root),
        "reports": directory_status(settings.reports_root),
        "backups": directory_status(settings.backups_root),
    }
    database = database_status(settings.database_path)
    migration: dict[str, object] = {
        "current_revision": None,
        "expected_revision": None,
        "current": False,
    }
    if database["readable"]:
        try:
            current = current_revision(settings.database_path)
            expected = expected_revision(settings.database_path)
            migration = {
                "current_revision": current,
                "expected_revision": expected,
                "current": current == expected,
            }
        except Exception:
            migration = {"current_revision": None, "expected_revision": None, "current": False}
    ready = bool(database.get("readable", False)) and bool(migration["current"]) and all(
        value["exists"] for value in directories.values()
    )
    return ready, {"database": database, "migration": migration, "directories": directories}
