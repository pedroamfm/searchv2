"""Minimal B01 worker process with a health heartbeat.

The persistent job loop is introduced in B06. This process proves container,
configuration and lifecycle boundaries without touching the analytical database.
"""

from __future__ import annotations

import json
import signal
import time
import importlib
import logging
from uuid import uuid4
from datetime import UTC, datetime
from pathlib import Path

from app import __version__
from app.config import get_settings
from app.database import database_connection
from app.jobs import JobService
from app.online_report import generate_online_report, run_enrichment_capture, update_daily_catalog, update_daily_highlights


class Worker:
    def __init__(self, heartbeat_path: Path, interval_seconds: float, database_path: Path | None = None) -> None:
        self.heartbeat_path = heartbeat_path
        self.interval_seconds = interval_seconds
        self.running = True
        self.database_path = database_path
        self.worker_id = f"worker-{uuid4()}"

    def stop(self, _signum: int, _frame: object) -> None:
        self.running = False

    def heartbeat(self) -> None:
        payload = {
            "service": "worker",
            "status": "running",
            "version": __version__,
            "heartbeat_at_utc": datetime.now(UTC).isoformat(),
        }
        temporary = self.heartbeat_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        temporary.replace(self.heartbeat_path)

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        while self.running:
            self.heartbeat()
            if self.database_path:
                with database_connection(self.database_path, read_only=False) as connection:
                    job = JobService().claim(connection, self.worker_id)
                    if job:
                        failed = False
                        try:
                            # Legacy commands remain callable; B06 moves their invocation out of HTTP.
                            if job["job_type"] == "report":
                                generate_online_report(get_settings())
                            elif job["job_type"] == "capture":
                                scope = __import__("json").loads(job["request_payload_json"])["scope"]
                                if scope == "daily_highlights": update_daily_highlights(get_settings())
                                elif scope == "daily_catalog": update_daily_catalog(get_settings())
                                elif scope in {"sellers", "keyword_supply", "expanded_visits", "shipping"}: run_enrichment_capture(get_settings(), scope)
                                else: importlib.import_module("examples.11_capture_report_sources").main()
                            else:
                                module = {"ingest": "examples.16_ingest_raw_to_sqlite", "render_pdf": "tools.render_markdown_pdf"}[job["job_type"]]
                                importlib.import_module(module).main()
                        except Exception:  # detailed exception stays in worker logs, not the API response
                            logging.exception("job execution failed", extra={"job_id": job["job_id"]})
                            failed = True
                        JobService().complete(connection, job["job_id"], self.worker_id, failed)
            time.sleep(self.interval_seconds)


def main() -> None:
    settings = get_settings()
    Worker(
        heartbeat_path=settings.worker_heartbeat_path,
        interval_seconds=settings.worker_poll_seconds,
        database_path=settings.database_path,
    ).run()


if __name__ == "__main__":
    main()
