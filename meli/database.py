"""SQLite persistence layer for Product Radar snapshots."""

import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/product_radar.sqlite3")


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capture_runs (
    capture_run_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    started_at_utc TEXT,
    finished_at_utc TEXT,
    manifest_path TEXT NOT NULL UNIQUE,
    raw_file_count INTEGER,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_sources (
    raw_source_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    capture_run_id INTEGER REFERENCES capture_runs(capture_run_id),
    relative_path TEXT NOT NULL UNIQUE,
    endpoint TEXT,
    captured_at_utc TEXT NOT NULL,
    http_status INTEGER,
    sha256 TEXT NOT NULL,
    ingested_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS category_snapshots (
    category_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    category_id TEXT NOT NULL,
    name TEXT,
    parent_category_id TEXT,
    level INTEGER,
    total_items INTEGER,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, category_id, parent_category_id, captured_at_utc, raw_source_id)
);

CREATE TABLE IF NOT EXISTS trend_snapshots (
    trend_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    site_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK(scope IN ('general', 'category')),
    category_id TEXT,
    position INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    url TEXT,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, site_id, scope, category_id, position, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS highlight_snapshots (
    highlight_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    site_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, site_id, category_id, position, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS product_snapshots (
    product_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    product_id TEXT NOT NULL,
    ranking_category_id TEXT,
    highlight_position INTEGER,
    name TEXT,
    brand TEXT,
    domain_id TEXT,
    family_name TEXT,
    status TEXT,
    sold_quantity INTEGER,
    has_buy_box_winner INTEGER NOT NULL DEFAULT 0,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, product_id, ranking_category_id, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS offer_snapshots (
    offer_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    product_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    seller_id TEXT,
    category_id TEXT,
    price REAL,
    original_price REAL,
    currency_id TEXT,
    condition TEXT,
    free_shipping INTEGER,
    official_store_id TEXT,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, product_id, item_id, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS visit_snapshots (
    visit_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    item_id TEXT NOT NULL,
    date_utc TEXT NOT NULL,
    visits INTEGER NOT NULL,
    window_days INTEGER,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, item_id, date_utc, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS keyword_product_mappings (
    keyword_product_mapping_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    site_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    category_id TEXT,
    trend_position INTEGER,
    keyword TEXT NOT NULL,
    product_id TEXT NOT NULL,
    relevance_position INTEGER NOT NULL,
    product_name TEXT,
    product_brand TEXT,
    domain_id TEXT,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, site_id, scope, category_id, keyword, product_id, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS product_category_snapshots (
    product_category_snapshot_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    product_id TEXT NOT NULL,
    ranking_category_id TEXT,
    offer_category_id TEXT,
    offer_category_name TEXT,
    path_json TEXT NOT NULL,
    offer_count INTEGER NOT NULL,
    captured_at_utc TEXT NOT NULL,
    raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id),
    UNIQUE(source_id, product_id, ranking_category_id, offer_category_id, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS seller_snapshots (seller_snapshot_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(source_id), seller_id TEXT NOT NULL, nickname TEXT, registration_date TEXT, state TEXT, city TEXT, captured_at_utc TEXT NOT NULL, raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id), UNIQUE(source_id, seller_id, captured_at_utc));
CREATE TABLE IF NOT EXISTS seller_reputation_snapshots (seller_reputation_snapshot_id INTEGER PRIMARY KEY, seller_id TEXT NOT NULL, level_id TEXT, power_seller_status TEXT, completed INTEGER, canceled INTEGER, captured_at_utc TEXT NOT NULL, raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id), UNIQUE(seller_id, captured_at_utc));
CREATE TABLE IF NOT EXISTS visit_sample_selections (visit_sample_selection_id INTEGER PRIMARY KEY, product_id TEXT NOT NULL, item_id TEXT NOT NULL, selection_reason TEXT NOT NULL, captured_at_utc TEXT NOT NULL, raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id), UNIQUE(product_id, item_id, selection_reason, captured_at_utc));
CREATE TABLE IF NOT EXISTS keyword_supply_snapshots (keyword_supply_snapshot_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(source_id), keyword TEXT NOT NULL, portfolio TEXT, result_count INTEGER, captured_at_utc TEXT NOT NULL, raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id), UNIQUE(source_id, keyword, captured_at_utc));
CREATE TABLE IF NOT EXISTS category_attribute_definitions (category_attribute_definition_id INTEGER PRIMARY KEY, category_id TEXT NOT NULL, attribute_id TEXT NOT NULL, name TEXT, value_type TEXT, captured_at_utc TEXT NOT NULL, raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id), UNIQUE(category_id, attribute_id, captured_at_utc));
CREATE TABLE IF NOT EXISTS shipping_option_snapshots (shipping_option_snapshot_id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, destination_code TEXT NOT NULL, shipping_mode TEXT, currency_id TEXT, cost REAL, list_cost REAL, estimated_delivery_from TEXT, estimated_delivery_to TEXT, captured_at_utc TEXT NOT NULL, raw_source_id INTEGER NOT NULL REFERENCES raw_sources(raw_source_id), UNIQUE(item_id, destination_code, shipping_mode, cost, captured_at_utc));

CREATE INDEX IF NOT EXISTS idx_trend_snapshot_lookup
    ON trend_snapshots(source_id, site_id, scope, category_id, captured_at_utc);
CREATE INDEX IF NOT EXISTS idx_highlight_snapshot_lookup
    ON highlight_snapshots(source_id, category_id, captured_at_utc, position);
CREATE INDEX IF NOT EXISTS idx_product_snapshot_lookup
    ON product_snapshots(source_id, product_id, captured_at_utc);
CREATE INDEX IF NOT EXISTS idx_offer_snapshot_lookup
    ON offer_snapshots(source_id, product_id, captured_at_utc);
CREATE INDEX IF NOT EXISTS idx_visit_snapshot_lookup
    ON visit_snapshots(source_id, item_id, date_utc, captured_at_utc);
CREATE INDEX IF NOT EXISTS idx_keyword_mapping_lookup
    ON keyword_product_mappings(source_id, keyword, captured_at_utc);

CREATE VIEW IF NOT EXISTS v_product_demand_snapshot AS
SELECT
    product_id,
    ranking_category_id,
    highlight_position,
    name,
    brand,
    domain_id,
    captured_at_utc,
    sold_quantity
FROM product_snapshots;
"""


def connect(path: Path | str = DATABASE_PATH) -> sqlite3.Connection:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.create_function("CASEFOLD", 1, lambda value: str(value).casefold() if value is not None else "")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    # Analytical tables predate Alembic; upgrade their additive fields here so
    # existing local evidence stores remain usable without destructive rebuilds.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(keyword_supply_snapshots)")}
    if "portfolio" not in columns:
        connection.execute("ALTER TABLE keyword_supply_snapshots ADD COLUMN portfolio TEXT")
    connection.execute(
        "INSERT OR IGNORE INTO sources (code, name) VALUES (?, ?)",
        ("mercado_libre", "Mercado Libre"),
    )
    # SQLite considers NULL values distinct in UNIQUE constraints. Normalize
    # optional key parts so re-importing general trends and root categories is
    # genuinely idempotent, then remove duplicates created by older imports.
    connection.executescript(
        """
        DELETE FROM trend_snapshots
        WHERE trend_snapshot_id NOT IN (
            SELECT MIN(trend_snapshot_id) FROM trend_snapshots
            GROUP BY source_id, site_id, scope, COALESCE(category_id, ''), position, captured_at_utc
        );
        UPDATE trend_snapshots SET category_id = '' WHERE category_id IS NULL;

        DELETE FROM keyword_product_mappings
        WHERE keyword_product_mapping_id NOT IN (
            SELECT MIN(keyword_product_mapping_id) FROM keyword_product_mappings
            GROUP BY source_id, site_id, scope, COALESCE(category_id, ''), keyword, product_id, captured_at_utc
        );
        UPDATE keyword_product_mappings SET category_id = '' WHERE category_id IS NULL;

        DELETE FROM category_snapshots
        WHERE category_snapshot_id NOT IN (
            SELECT MIN(category_snapshot_id) FROM category_snapshots
            GROUP BY source_id, category_id, COALESCE(parent_category_id, ''), captured_at_utc, raw_source_id
        );
        UPDATE category_snapshots SET parent_category_id = '' WHERE parent_category_id IS NULL;
        """
    )
    connection.commit()
