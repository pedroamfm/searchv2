import tempfile
from pathlib import Path

import pytest

from app.auth import create_admin
from app.config import AppSettings
from app.database import database_connection
from app.errors import ApiError
from app.jobs import JobService
from app.migrations import upgrade
from meli.database import initialize


def test_job_is_idempotent_claimed_and_completed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        settings = AppSettings(_env_file=None, database_path=root / "data/radar.sqlite3", raw_root=root / "raw", reports_root=root / "reports", backups_root=root / "backups")
        settings.database_path.parent.mkdir(parents=True)
        with database_connection(settings.database_path, read_only=False) as connection:
            initialize(connection)
        upgrade(settings, create_backup=False)
        service = JobService()
        with database_connection(settings.database_path, read_only=False) as connection:
            create_admin(connection, "admin@example.test", "Admin", "correct-password")
            user_id = connection.execute("SELECT user_id FROM app_users").fetchone()[0]
            first = service.enqueue(connection, job_type="capture", source_code="mercado_libre", site_id="MLC", scope="full", actor_user_id=user_id, idempotency_key="same-request-key")
            assert service.enqueue(connection, job_type="capture", source_code="mercado_libre", site_id="MLC", scope="full", actor_user_id=user_id, idempotency_key="same-request-key")["job_id"] == first["job_id"]
            with pytest.raises(ApiError) as active:
                service.enqueue(connection, job_type="capture", source_code="mercado_libre", site_id="MLC", scope="full", actor_user_id=user_id, idempotency_key="another-request-key")
            assert active.value.code == "active_capture_exists"
            claimed = service.claim(connection, "test-worker")
            assert claimed and claimed["status"] == "running"
            service.complete(connection, claimed["job_id"], "test-worker")
            assert connection.execute("SELECT status FROM jobs WHERE job_id=?", (claimed["job_id"],)).fetchone()[0] == "succeeded"
            assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=?", (claimed["job_id"],)).fetchone()[0] == 3
