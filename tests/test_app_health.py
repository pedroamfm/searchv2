import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.config import AppSettings
from app.health import readiness
from app.migrations import upgrade


class ReadinessTests(unittest.TestCase):
    def settings(self, root: Path) -> AppSettings:
        return AppSettings(
            _env_file=None,
            database_path=root / "data" / "product_radar.sqlite3",
            raw_root=root / "data" / "raw",
            reports_root=root / "reports",
            backups_root=root / "backups",
        )

    def test_ready_when_database_and_directories_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            for directory in settings.required_directories():
                directory.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(settings.database_path)
            connection.close()
            upgrade(settings, create_backup=False)

            ready, checks = readiness(settings)

            self.assertTrue(ready)
            self.assertTrue(checks["database"]["readable"])
            self.assertTrue(checks["migration"]["current"])

    def test_not_ready_when_database_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            for directory in settings.required_directories():
                directory.mkdir(parents=True, exist_ok=True)

            ready, checks = readiness(settings)

            self.assertFalse(ready)
            self.assertFalse(checks["database"]["exists"])


if __name__ == "__main__":
    unittest.main()
