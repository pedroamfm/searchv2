"""Typed runtime configuration shared by the API and worker."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "Product Radar"
    environment: str = "development"
    public_base_url: str = "http://localhost:3000"
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    database_path: Path = Path("data/product_radar.sqlite3")
    raw_root: Path = Path("data/raw")
    reports_root: Path = Path("reports")
    backups_root: Path = Path("backups")
    log_level: str = "INFO"
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    worker_heartbeat_path: Path = Path("/tmp/product-radar-worker-heartbeat")
    worker_heartbeat_seconds: float = Field(default=10.0, gt=0, le=60)
    session_hours: int = Field(default=8, ge=1, le=168)
    login_max_failures: int = Field(default=5, ge=1, le=20)
    login_lock_minutes: int = Field(default=15, ge=1, le=1440)
    enrichment_seller_limit: int = Field(default=100, ge=1, le=500)
    enrichment_keyword_limit: int = Field(default=20, ge=1, le=50)
    enrichment_items_per_product: int = Field(default=5, ge=1, le=5)
    enrichment_shipping_item_limit: int = Field(default=20, ge=1, le=100)
    enrichment_destination_zip_codes: str = "8320000,2340000,4030000,1240000"

    def required_directories(self) -> tuple[Path, ...]:
        return (
            self.database_path.parent,
            self.raw_root,
            self.reports_root,
            self.backups_root,
        )


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
