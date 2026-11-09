"""Emit a deterministic, secret-free snapshot of the Product Radar baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_TABLES = (
    "sources",
    "capture_runs",
    "raw_sources",
    "category_snapshots",
    "trend_snapshots",
    "highlight_snapshots",
    "product_snapshots",
    "offer_snapshots",
    "visit_snapshots",
    "keyword_product_mappings",
    "product_category_snapshots",
)

KEY_FILES = (
    "requirements.txt",
    "meli/database.py",
    "meli/report_config.py",
    "examples/11_capture_report_sources.py",
    "examples/13_generate_report.py",
    "examples/16_ingest_raw_to_sqlite.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_summary(root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    if not root.exists():
        return {"file_count": 0, "total_bytes": 0, "sha256": None}

    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        file_hash = sha256_file(path)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        file_count += 1
        total_bytes += size

    return {
        "file_count": file_count,
        "total_bytes": total_bytes,
        "sha256": digest.hexdigest(),
    }


def database_summary(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        existing = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in DEFAULT_TABLES
            if table in existing
        }
    finally:
        connection.close()

    return {
        "relative_path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "integrity_check": integrity,
        "user_version": user_version,
        "table_counts": counts,
    }


def latest_manifest(root: Path) -> dict[str, Any] | None:
    manifests = sorted((root / "data/raw/capture_runs").glob("*.json"))
    if not manifests:
        return None
    path = manifests[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "site_id": payload.get("site_id"),
        "started_at_utc": payload.get("started_at_utc"),
        "finished_at_utc": payload.get("finished_at_utc"),
        "raw_file_count": payload.get("raw_file_count"),
        "modules": payload.get("modules", []),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica integridad, conteos y hashes sin modificar el repositorio."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/product_radar.sqlite3"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    database = args.database
    if not database.is_absolute():
        database = root / database
    if not database.is_file():
        raise FileNotFoundError(f"No existe la base: {database}")

    key_hashes = {}
    for relative in KEY_FILES:
        path = root / relative
        key_hashes[relative] = sha256_file(path) if path.is_file() else None

    result = {
        "format_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "database": database_summary(database),
        "raw_tree": tree_summary(root / "data/raw"),
        "reports_tree": tree_summary(root / "reports"),
        "latest_capture_manifest": latest_manifest(root),
        "key_file_sha256": key_hashes,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
