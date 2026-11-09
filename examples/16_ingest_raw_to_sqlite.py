"""Load existing Mercado Libre RAW JSON snapshots into SQLite idempotently."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from meli.database import connect, initialize


ROOT = Path(".")
TIMESTAMP = re.compile(r"_(\d{8}_\d{6})\.json$")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def captured_at(path: Path) -> str:
    match = TIMESTAMP.search(path.name)
    if not match:
        raise ValueError(f"No se encontró timestamp en {path}")
    return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S").replace(
        tzinfo=timezone.utc
    ).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def endpoint_for(path: Path) -> str:
    text = str(path)
    if "/trends/categories/" in text:
        return "/trends/{site}/{category_id}"
    if "/trends/" in text:
        return "/trends/{site}"
    if "/highlights/" in text:
        return "/highlights/{site}/category/{category_id}"
    if "/catalog_coverage/products/" in text:
        return "/products/{product_id}"
    if "/catalog_coverage/offers/" in text:
        return "/products/{product_id}/items"
    if "/catalog_coverage/visits/" in text:
        return "/items/{item_id}/visits/time_window"
    if "/expanded_visits/" in text:
        return "/items/{item_id}/visits/time_window"
    if "/sellers/" in text:
        return "/users/{seller_id}"
    if "/keyword_supply/" in text:
        return "/products/search"
    if "/category_attributes/" in text:
        return "/categories/{category_id}/attributes"
    if "/shipping_options/" in text:
        return "/items/{item_id}/shipping_options"
    if "/keyword_products/" in text:
        return "/products/search"
    if "/category_details/" in text:
        return "/categories/{category_id}"
    if "/categories/" in text:
        return "/sites/{site}/categories"
    return "raw"


def source_id(connection) -> int:
    return connection.execute(
        "SELECT source_id FROM sources WHERE code = 'mercado_libre'"
    ).fetchone()[0]


def raw_id(connection, source: int, path: Path, run_ids: dict[str, int]) -> int:
    contents = path.read_bytes()
    relative = rel(path)
    connection.execute(
        """
        INSERT INTO raw_sources (
            source_id, capture_run_id, relative_path, endpoint, captured_at_utc,
            sha256, ingested_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(relative_path) DO UPDATE SET
            capture_run_id = excluded.capture_run_id,
            sha256 = excluded.sha256,
            ingested_at_utc = excluded.ingested_at_utc
        """,
        (
            source,
            run_ids.get(relative),
            relative,
            endpoint_for(path),
            captured_at(path),
            hashlib.sha256(contents).hexdigest(),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return connection.execute(
        "SELECT raw_source_id FROM raw_sources WHERE relative_path = ?", (relative,)
    ).fetchone()[0]


def create_runs(connection, source: int) -> dict[str, int]:
    run_ids: dict[str, int] = {}
    for path in sorted(Path("data/raw/capture_runs").glob("*.json")):
        payload = load(path)
        connection.execute(
            """
            INSERT INTO capture_runs (
                source_id, started_at_utc, finished_at_utc, manifest_path,
                raw_file_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(manifest_path) DO UPDATE SET
                finished_at_utc = excluded.finished_at_utc,
                raw_file_count = excluded.raw_file_count,
                metadata_json = excluded.metadata_json
            """,
            (
                source,
                payload.get("started_at_utc"),
                payload.get("finished_at_utc"),
                rel(path),
                payload.get("raw_file_count"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        run_id = connection.execute(
            "SELECT capture_run_id FROM capture_runs WHERE manifest_path = ?", (rel(path),)
        ).fetchone()[0]
        run_ids.update({entry: run_id for entry in payload.get("raw_files", [])})
    return run_ids


def trend_rows(data: Any) -> list[dict[str, Any]]:
    """Return valid trend rows while preserving non-list payloads only as RAW."""
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def ingest_trends(connection, source: int, run_ids: dict[str, int]) -> None:
    paths = list(Path("data/raw/trends").glob("trends_mlc_*.json"))
    paths += list(Path("data/raw/trends/categories").glob("trends_mlc_*.json"))
    for path in sorted(paths):
        data = load(path)
        raw = raw_id(connection, source, path, run_ids)
        parts = path.stem.split("_")
        category_id = parts[2].upper() if "categories" in path.parts else None
        scope = "category" if category_id else "general"
        for position, row in enumerate(trend_rows(data), 1):
            connection.execute(
                """INSERT OR IGNORE INTO trend_snapshots
                (source_id, site_id, scope, category_id, position, keyword, url, captured_at_utc, raw_source_id)
                VALUES (?, 'MLC', ?, ?, ?, ?, ?, ?, ?)""",
                (source, scope, category_id or "", position, row.get("keyword"), row.get("url"), captured_at(path), raw),
            )


def ingest_highlights(connection, source: int, run_ids: dict[str, int]) -> None:
    for path in sorted(Path("data/raw/highlights").glob("highlights_mlc_*.json")):
        data = load(path)
        raw = raw_id(connection, source, path, run_ids)
        category_id = path.stem.split("_")[2].upper()
        for row in data.get("content", []):
            connection.execute(
                """INSERT OR IGNORE INTO highlight_snapshots
                (source_id, site_id, category_id, position, entity_type, entity_id, captured_at_utc, raw_source_id)
                VALUES (?, 'MLC', ?, ?, ?, ?, ?, ?)""",
                (source, category_id, row.get("position"), row.get("type"), row.get("id"), captured_at(path), raw),
            )


def latest_related(path: Path) -> Path:
    return path


def same_capture_day(paths: list[Path], capture_time: str) -> Path | None:
    matching = [path for path in paths if captured_at(path)[:10] == capture_time[:10]]
    return max(matching, key=captured_at) if matching else None


def ingest_coverage(connection, source: int, run_ids: dict[str, int]) -> None:
    for path in sorted(Path("data/raw/catalog_coverage").glob("catalog_coverage_report_*.json")):
        data = load(path)
        coverage_raw = raw_id(connection, source, path, run_ids)
        captured = captured_at(path)
        for row in data.get("products", []):
            product_id = row["product_id"]
            product_paths = sorted(
                Path("data/raw/catalog_coverage/products").glob(f"product_{product_id.lower()}_*.json")
            )
            product_path = same_capture_day(product_paths, captured)
            product_raw = raw_id(connection, source, product_path, run_ids) if product_path else coverage_raw
            family_name = load(product_path).get("family_name") if product_path else None
            connection.execute(
                """INSERT OR IGNORE INTO product_snapshots
                (source_id, product_id, ranking_category_id, highlight_position, name, brand, domain_id,
                 family_name, status, sold_quantity, has_buy_box_winner, captured_at_utc, raw_source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (source, product_id, row.get("category_id"), row.get("highlight_position"), row.get("name"),
                 row.get("brand"), row.get("domain_id"), family_name, row.get("status"),
                 row.get("sold_quantity"), int(bool(row.get("has_buy_box_winner"))), captured, product_raw),
            )
            offer_paths = sorted(
                Path("data/raw/catalog_coverage/offers").glob(f"offers_{product_id.lower()}_*.json")
            )
            offer_path = same_capture_day(offer_paths, captured)
            if not offer_path:
                continue
            offers_raw = raw_id(connection, source, offer_path, run_ids)
            for offer in load(offer_path).get("results", []):
                connection.execute(
                    """INSERT OR IGNORE INTO offer_snapshots
                    (source_id, product_id, item_id, seller_id, category_id, price, original_price,
                     currency_id, condition, free_shipping, official_store_id, captured_at_utc, raw_source_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source, product_id, offer.get("item_id"), str(offer.get("seller_id") or ""),
                     offer.get("category_id"), offer.get("price"), offer.get("original_price"),
                     offer.get("currency_id"), offer.get("condition"),
                     int(bool((offer.get("shipping") or {}).get("free_shipping"))),
                     str(offer.get("official_store_id") or ""), captured, offers_raw),
                )
            sample = row.get("visit_sample") or {}
            item_id = sample.get("item_id")
            if not item_id:
                continue
            visits = sorted(Path("data/raw/catalog_coverage/visits").glob(f"visits_{item_id.lower()}_*.json"))
            visit_path = same_capture_day(visits, captured)
            if not visit_path:
                continue
            visit_raw = raw_id(connection, source, visit_path, run_ids)
            visit_data = load(visit_path)
            for point in visit_data.get("results", []):
                connection.execute(
                    """INSERT OR IGNORE INTO visit_snapshots
                    (source_id, item_id, date_utc, visits, window_days, captured_at_utc, raw_source_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (source, item_id, point["date"], point["total"], visit_data.get("last"), captured, visit_raw),
                )


def ingest_keyword_maps(connection, source: int, run_ids: dict[str, int]) -> None:
    for path in sorted(Path("data/raw/keyword_products").glob("keyword_product_map_mlc_*.json")):
        data = load(path)
        raw = raw_id(connection, source, path, run_ids)
        for mapping in data.get("mappings", []):
            for product in mapping.get("products", []):
                connection.execute(
                    """INSERT OR IGNORE INTO keyword_product_mappings
                    (source_id, site_id, scope, category_id, trend_position, keyword, product_id,
                     relevance_position, product_name, product_brand, domain_id, captured_at_utc, raw_source_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source, data.get("site_id", "MLC"), mapping.get("scope"), mapping.get("category_id") or "",
                     mapping.get("trend_position"), mapping.get("keyword"), product.get("product_id"),
                     product.get("relevance_position"), product.get("name"), product.get("brand"),
                     product.get("domain_id"), mapping.get("captured_at_utc"), raw),
                )


def ingest_hierarchies(connection, source: int, run_ids: dict[str, int]) -> None:
    for path in sorted(Path("data/raw/category_details").glob("category_hierarchy_mlc_*.json")):
        data = load(path)
        raw = raw_id(connection, source, path, run_ids)
        captured = data["captured_at_utc"]
        for category_id, category in data.get("categories", {}).items():
            path_nodes = category.get("path_from_root", [])
            parent = path_nodes[-2]["id"] if len(path_nodes) > 1 else None
            connection.execute(
                """INSERT OR IGNORE INTO category_snapshots
                (source_id, category_id, name, parent_category_id, level, total_items, captured_at_utc, raw_source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (source, category_id, category.get("name"), parent or "", len(path_nodes),
                 category.get("total_items_in_this_category"), captured, raw),
            )


def ingest_enrichments(connection, source: int, run_ids: dict[str, int]) -> None:
    for path in sorted(Path("data/raw/sellers").glob("seller_*.json")):
        data, raw, captured = load(path), raw_id(connection, source, path, run_ids), captured_at(path)
        profile, reputation, address = data.get("profile") or {}, (data.get("profile") or {}).get("seller_reputation") or {}, (data.get("profile") or {}).get("address") or {}
        connection.execute("INSERT OR IGNORE INTO seller_snapshots (source_id,seller_id,nickname,registration_date,state,city,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?,?,?,?)", (source, str(data.get("seller_id")), profile.get("nickname"), profile.get("registration_date"), address.get("state"), address.get("city"), captured, raw))
        connection.execute("INSERT OR IGNORE INTO seller_reputation_snapshots (seller_id,level_id,power_seller_status,completed,canceled,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?,?,?)", (str(data.get("seller_id")), reputation.get("level_id"), reputation.get("power_seller_status"), (reputation.get("transactions") or {}).get("completed"), (reputation.get("transactions") or {}).get("canceled"), captured, raw))
    for path in sorted(Path("data/raw/expanded_visits").glob("visits_*.json")):
        data, raw, captured = load(path), raw_id(connection, source, path, run_ids), captured_at(path); visits, item_id = data.get("visits") or {}, str(data.get("item_id"))
        connection.execute("INSERT OR IGNORE INTO visit_sample_selections (product_id,item_id,selection_reason,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?)", (data.get("product_id"), item_id, data.get("selection_reason"), captured, raw))
        for point in visits.get("results", []): connection.execute("INSERT OR IGNORE INTO visit_snapshots (source_id,item_id,date_utc,visits,window_days,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?,?,?)", (source, item_id, point.get("date"), point.get("total"), visits.get("last"), captured, raw))
    for path in sorted(Path("data/raw/keyword_supply").glob("*.json")):
        data, raw, captured = load(path), raw_id(connection, source, path, run_ids), captured_at(path); supply = data.get("supply") or {}
        connection.execute("INSERT OR IGNORE INTO keyword_supply_snapshots (source_id,keyword,portfolio,result_count,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?,?)", (source, data.get("keyword"), data.get("portfolio"), (supply.get("paging") or {}).get("total", len(supply.get("results") or [])), captured, raw))
    for path in sorted(Path("data/raw/category_attributes").glob("*.json")):
        data, raw, captured = load(path), raw_id(connection, source, path, run_ids), captured_at(path)
        for item in data.get("attributes") or []: connection.execute("INSERT OR IGNORE INTO category_attribute_definitions (category_id,attribute_id,name,value_type,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?,?)", (data.get("category_id"), item.get("id"), item.get("name"), item.get("value_type"), captured, raw))
    for path in sorted(Path("data/raw/shipping_options").glob("*.json")):
        data, raw, captured = load(path), raw_id(connection, source, path, run_ids), captured_at(path); payload = data.get("options") or {}
        for item in payload.get("options", []) if isinstance(payload, dict) else []:
            delivery = item.get("estimated_delivery") or {}; connection.execute("INSERT OR IGNORE INTO shipping_option_snapshots (item_id,destination_code,shipping_mode,currency_id,cost,list_cost,estimated_delivery_from,estimated_delivery_to,captured_at_utc,raw_source_id) VALUES (?,?,?,?,?,?,?,?,?,?)", (data.get("item_id"), data.get("destination_code"), item.get("name") or item.get("shipping_method_type"), item.get("currency_id"), item.get("cost"), item.get("list_cost"), delivery.get("date"), delivery.get("date"), captured, raw))
        for row in data.get("product_categories", []):
            connection.execute(
                """INSERT OR IGNORE INTO product_category_snapshots
                (source_id, product_id, ranking_category_id, offer_category_id, offer_category_name,
                 path_json, offer_count, captured_at_utc, raw_source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (source, row["product_id"], row.get("ranking_category_id"),
                 row.get("primary_offer_category_id"), row.get("primary_category_name"),
                 json.dumps(row.get("primary_category_path", []), ensure_ascii=False),
                 sum(row.get("offer_category_counts", {}).values()), captured, raw),
            )


def main() -> None:
    connection = connect()
    try:
        initialize(connection)
        source = source_id(connection)
        with connection:
            run_ids = create_runs(connection, source)
            ingest_trends(connection, source, run_ids)
            ingest_highlights(connection, source, run_ids)
            ingest_coverage(connection, source, run_ids)
            ingest_keyword_maps(connection, source, run_ids)
            ingest_hierarchies(connection, source, run_ids)
            ingest_enrichments(connection, source, run_ids)
        for table in (
            "capture_runs", "raw_sources", "category_snapshots", "trend_snapshots",
            "highlight_snapshots", "product_snapshots", "offer_snapshots", "visit_snapshots",
            "keyword_product_mappings", "product_category_snapshots",
        ):
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
