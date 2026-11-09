import json
import importlib
from pathlib import Path

from app.config import AppSettings
from app.online_report import refresh_worker_token


def test_refresh_worker_token_rotates_and_persists(monkeypatch, tmp_path: Path) -> None:
    settings = AppSettings(_env_file=None, database_path=tmp_path / "data/radar.sqlite3", raw_root=tmp_path / "raw", reports_root=tmp_path / "reports", backups_root=tmp_path / "backups")
    calls: list[str | None] = []
    monkeypatch.setattr("app.online_report.refresh_access_token", lambda token=None: calls.append(token) or {"access_token": "new-access", "refresh_token": "new-refresh"})
    refresh_worker_token(settings)
    refresh_worker_token(settings)
    assert calls == [None, "new-refresh"]
    assert json.loads((settings.backups_root / ".meli_oauth_tokens.json").read_text())["refresh_token"] == "new-refresh"


def test_visit_metrics_keeps_its_item_id(monkeypatch, tmp_path: Path) -> None:
    """Traffic rendering must not depend on a possibly duplicated product row."""
    visits = tmp_path / "data/raw/catalog_coverage/visits"
    visits.mkdir(parents=True)
    (visits / "visits_mlc123_20260922_120000.json").write_text(
        json.dumps(
            {
                "total_visits": 12,
                "results": [{"date": "2026-09-22T00:00:00Z", "total": 12}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    generator = importlib.import_module("examples.13_generate_report")
    metrics = generator.visit_metrics("MLC123")

    assert metrics["item_id"] == "MLC123"
    assert metrics["total_30d"] == 12
