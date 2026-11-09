"""Versioned migration and backup operations for the SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.config import AppSettings, get_settings


def alembic_config(database_path: Path) -> Config:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_path"] = database_path
    return config


def expected_revision(database_path: Path) -> str:
    script = ScriptDirectory.from_config(alembic_config(database_path))
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("No hay revisiones Alembic disponibles.")
    return head


def current_revision(database_path: Path) -> str | None:
    if not database_path.is_file():
        return None
    engine = create_engine(f"sqlite:///{database_path.resolve()}")
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def is_current(database_path: Path) -> bool:
    return current_revision(database_path) == expected_revision(database_path)


def backup_database(database_path: Path, backups_root: Path) -> Path:
    """Create a consistent SQLite backup without copying WAL files directly."""
    backups_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = backups_root / f"product_radar_before_migration_{timestamp}.sqlite3"
    source = sqlite3.connect(database_path)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return destination


def upgrade(settings: AppSettings, *, create_backup: bool = True) -> Path | None:
    database_path = settings.database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if create_backup and database_path.is_file() and not is_current(database_path):
        backup = backup_database(database_path, settings.backups_root)
    command.upgrade(alembic_config(database_path), "head")
    return backup


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate Product Radar SQLite schema.")
    parser.add_argument("command", choices=("upgrade", "current"))
    parser.add_argument("--no-backup", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    if args.command == "current":
        print(current_revision(settings.database_path) or "unversioned")
        return
    backup = upgrade(settings, create_backup=not args.no_backup)
    if backup is not None:
        print(f"Backup consistente creado: {backup.name}")
    print(f"Migración aplicada: {expected_revision(settings.database_path)}")


if __name__ == "__main__":
    main()
