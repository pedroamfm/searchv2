import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import Request, Response

from app.config import AppSettings
from app.main import app, live, ready, request_id
from app.migrations import upgrade


class ApiHealthTests(unittest.TestCase):
    def test_live_endpoint(self) -> None:
        payload = live()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "api")

    def test_ready_endpoint(self) -> None:
        async def invoke_ready() -> tuple[Response, dict[str, object]]:
            async with app.router.lifespan_context(app):
                response = Response()
                return response, ready(response)

        # Readiness must use a migrated temporary database, never the operator's DB.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            configured = AppSettings(
                _env_file=None,
                database_path=root / "radar.db",
                raw_root=root / "raw",
                reports_root=root / "reports",
                backups_root=root / "backups",
            )
            for directory in configured.required_directories():
                directory.mkdir(parents=True, exist_ok=True)
            upgrade(configured, create_backup=False)
            with (
                patch("app.main.settings", configured),
                patch("app.main.get_settings", return_value=configured),
            ):
                response, payload = asyncio.run(invoke_ready())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ready")


if __name__ == "__main__":
    unittest.main()


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/api/v1/reports/weekly.pdf", "private, no-store"),
        ("/api/v1/auth/me", "private, no-store"),
        ("/api/v1/health/live", None),
    ],
)
def test_public_proxy_does_not_cache_private_api_data(path: str, expected: str | None) -> None:
    request = Request(
        {"type": "http", "scheme": "http", "path": path, "query_string": b"", "headers": []}
    )

    async def next_response(_: Request) -> Response:
        return Response("private response")

    response = asyncio.run(request_id(request, next_response))
    assert response.headers.get("Cache-Control") == expected
