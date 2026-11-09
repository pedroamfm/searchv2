"""Container health command for the B01 worker heartbeat."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    path = settings.worker_heartbeat_path
    if not path.is_file():
        raise SystemExit("worker heartbeat is missing")

    payload = json.loads(path.read_text(encoding="utf-8"))
    heartbeat = datetime.fromisoformat(payload["heartbeat_at_utc"])
    age = (datetime.now(UTC) - heartbeat).total_seconds()
    maximum_age = max(30.0, settings.worker_heartbeat_seconds * 3)
    if age > maximum_age:
        raise SystemExit(f"worker heartbeat is stale: {age:.1f}s")
    sys.stdout.write("ok\n")


if __name__ == "__main__":
    main()
