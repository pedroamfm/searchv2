import sqlite3
import tempfile
from pathlib import Path

from app.config import AppSettings
from app.migrations import backup_database, current_revision, expected_revision, upgrade


def settings(root: Path) -> AppSettings:
    return AppSettings(
        _env_file=None,
        database_path=root / "data" / "product_radar.sqlite3",
        raw_root=root / "data" / "raw",
        reports_root=root / "reports",
        backups_root=root / "backups",
    )


def test_upgrade_preserves_legacy_table_and_records_revision() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        configured = settings(Path(temporary))
        configured.database_path.parent.mkdir(parents=True)
        connection = sqlite3.connect(configured.database_path)
        connection.execute("CREATE TABLE sources (source_id INTEGER PRIMARY KEY, code TEXT)")
        connection.execute("INSERT INTO sources VALUES (1, 'mercado_libre')")
        connection.commit()
        connection.close()

        backup = upgrade(configured)

        assert backup is not None and backup.is_file()
        connection = sqlite3.connect(configured.database_path)
        try:
            assert connection.execute("SELECT code FROM sources").fetchone() == ("mercado_libre",)
            assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'jobs'").fetchone()
        finally:
            connection.close()
        assert current_revision(configured.database_path) == expected_revision(configured.database_path)


def test_backup_database_is_a_consistent_copy() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        database_path = root / "data" / "product_radar.sqlite3"
        database_path.parent.mkdir(parents=True)
        connection = sqlite3.connect(database_path)
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('preserved')")
        connection.commit()
        connection.close()

        backup = backup_database(database_path, root / "backups")

        copied = sqlite3.connect(backup)
        try:
            assert copied.execute("SELECT value FROM sample").fetchone() == ("preserved",)
        finally:
            copied.close()
