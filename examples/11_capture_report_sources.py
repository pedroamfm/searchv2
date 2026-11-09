import importlib
from datetime import datetime, timezone
from pathlib import Path

from meli.storage import save_json


CAPTURE_MODULES = (
    "examples.03_trends",
    "examples.04_categories",
    "examples.05_category_trends",
    "examples.12_keyword_products",
    "examples.06_highlights",
    "examples.09_catalog_coverage",
    "examples.14_category_hierarchy",
)


def raw_files() -> set[Path]:
    return set(Path("data/raw").rglob("*.json"))


def main() -> None:
    started_at = datetime.now(timezone.utc)
    before = raw_files()

    for module_name in CAPTURE_MODULES:
        print(f"\nEjecutando {module_name}")
        module = importlib.import_module(module_name)
        module.main()

    finished_at = datetime.now(timezone.utc)
    created = sorted(raw_files() - before)
    manifest = {
        "site_id": "MLC",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "modules": list(CAPTURE_MODULES),
        "raw_files": [str(path) for path in created],
        "raw_file_count": len(created),
    }
    filename = save_json(manifest, "data/raw/capture_runs", "capture_run_mlc")
    print(f"\nCaptura completa: {len(created)} archivos RAW")
    print(f"Manifiesto: {filename}")

    print("\nActualizando persistencia SQLite")
    importer = importlib.import_module("examples.16_ingest_raw_to_sqlite")
    importer.main()


if __name__ == "__main__":
    main()
