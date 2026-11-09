import os
import random
import time
import threading
from typing import Any

import requests


BASE_URL = "https://api.mercadolibre.com"


class _SharedRateLimiter:
    """One conservative request budget for every client using the worker token."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def wait(self, requests_per_second: float) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request_at - now)
            self._next_request_at = max(now, self._next_request_at) + (1.0 / requests_per_second)
        if delay:
            time.sleep(delay)


_rate_limiter = _SharedRateLimiter()


class MercadoLibreClient:
    def __init__(
        self,
        access_token: str | None = None,
        site_id: str | None = None,
        requests_per_second: float | None = None,
    ) -> None:
        self.access_token = access_token or os.getenv("MELI_ACCESS_TOKEN")
        self.site_id = site_id or os.getenv("MELI_SITE_ID", "MLC")
        self.requests_per_second = requests_per_second or float(os.getenv("MELI_REQUESTS_PER_SECOND", "3"))
        if self.requests_per_second <= 0:
            raise ValueError("MELI_REQUESTS_PER_SECOND debe ser mayor que cero")

        if not self.access_token:
            raise ValueError("Falta MELI_ACCESS_TOKEN")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            }
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self.get_response(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def get_response(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        if not endpoint.startswith("/"):
            raise ValueError("El endpoint debe comenzar con '/'")

        response = None
        for attempt in range(5):
            _rate_limiter.wait(self.requests_per_second)
            response = self.session.get(
                f"{BASE_URL}{endpoint}",
                params=params,
                timeout=30,
            )
            if response.status_code not in {429, 500, 502, 503, 504} or attempt == 4:
                break
            retry_after = response.headers.get("Retry-After")
            try:
                delay = min(60.0, float(retry_after)) if retry_after else min(30.0, 2.0 ** attempt) + random.uniform(0.0, 1.0)
            except ValueError:
                delay = min(30.0, 2.0 ** attempt) + random.uniform(0.0, 1.0)
            time.sleep(delay)
        assert response is not None
        print(f"GET {response.url} STATUS {response.status_code}")
        return response
