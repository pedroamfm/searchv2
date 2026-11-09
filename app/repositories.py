"""Read repositories for Product Radar analytical and operational data."""

from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from typing import cast


@dataclass(frozen=True)
class Page:
    rows: list[sqlite3.Row]
    next_cursor: int | None


def _page(connection: sqlite3.Connection, query: str, params: tuple[object, ...], limit: int) -> Page:
    rows = connection.execute(query, (*params, limit + 1)).fetchall()
    next_cursor = int(rows[limit - 1]["row_id"]) if len(rows) > limit else None
    return Page(rows=rows[:limit], next_cursor=next_cursor)


class SourceRepository:
    def list(self, connection: sqlite3.Connection) -> list[sqlite3.Row]:
        return connection.execute(
            "SELECT source_id, code, name FROM sources ORDER BY code"
        ).fetchall()


class CaptureRepository:
    def list(self, connection: sqlite3.Connection, *, cursor: int, limit: int) -> Page:
        return _page(
            connection,
            """
            SELECT capture_run_id AS row_id, capture_run_id, source_id, started_at_utc,
                   finished_at_utc, manifest_path, raw_file_count
            FROM capture_runs WHERE capture_run_id > ? ORDER BY capture_run_id ASC LIMIT ?
            """,
            (cursor,),
            limit,
        )


class TrendRepository:
    def list(
        self, connection: sqlite3.Connection, *, cursor: int, limit: int, source_code: str | None,
        scope: str | None, category_id: str | None, keyword: str | None, captured_from: str | None = None,
        captured_to: str | None = None
    ) -> Page:
        filters = "WHERE t.trend_snapshot_id > ?"
        params: list[object] = [cursor]
        if source_code is not None:
            filters += " AND s.code = ?"
            params.append(source_code)
        if scope is not None:
            filters += " AND t.scope = ?"
            params.append(scope)
        if category_id is not None:
            filters += " AND t.category_id = ?"
            params.append(category_id)
        if keyword is not None:
            filters += " AND CASEFOLD(t.keyword) LIKE ?"
            params.append(f"%{keyword.casefold()}%")
        if captured_from is not None:
            filters += " AND t.captured_at_utc >= ?"
            params.append(captured_from)
        if captured_to is not None:
            filters += " AND t.captured_at_utc <= ?"
            params.append(captured_to)
        return _page(
            connection,
            f"""
            WITH ranked AS (
                SELECT t.*, LAG(t.position) OVER (
                    PARTITION BY t.source_id, t.site_id, t.scope, t.category_id, t.keyword
                    ORDER BY t.captured_at_utc, t.trend_snapshot_id
                ) AS previous_position
                FROM trend_snapshots t
            )
            SELECT t.trend_snapshot_id AS row_id, s.code AS source_code, t.site_id, t.scope,
                   NULLIF(t.category_id, '') AS category_id, t.keyword, t.position,
                   t.previous_position,
                   CASE WHEN t.previous_position IS NULL THEN 'new'
                        WHEN t.position < t.previous_position THEN 'up'
                        WHEN t.position > t.previous_position THEN 'down'
                        ELSE 'unchanged' END AS change,
                   t.captured_at_utc, t.raw_source_id
            FROM ranked t JOIN sources s ON s.source_id = t.source_id
            {filters} ORDER BY t.trend_snapshot_id ASC LIMIT ?
            """,
            tuple(params),
            limit,
        )

    def history(
        self, connection: sqlite3.Connection, *, source_code: str, site_id: str,
        scope: str, category_id: str | None, keyword: str
    ) -> list[sqlite3.Row]:
        return connection.execute(
            """
            WITH ranked AS (
                SELECT t.*, LAG(t.position) OVER (ORDER BY t.captured_at_utc, t.trend_snapshot_id) AS previous_position
                FROM trend_snapshots t JOIN sources s ON s.source_id=t.source_id
                WHERE s.code=? AND t.site_id=? AND t.scope=? AND t.category_id=? AND CASEFOLD(t.keyword)=CASEFOLD(?)
            )
            SELECT trend_snapshot_id AS row_id, ? AS source_code, site_id, scope,
                   NULLIF(category_id, '') AS category_id, keyword, position, previous_position,
                   CASE WHEN previous_position IS NULL THEN 'new' WHEN position < previous_position THEN 'up'
                        WHEN position > previous_position THEN 'down' ELSE 'unchanged' END AS change,
                   captured_at_utc, raw_source_id
            FROM ranked ORDER BY captured_at_utc ASC, trend_snapshot_id ASC
            """,
            (source_code, site_id, scope, category_id or "", keyword, source_code),
        ).fetchall()

    def categories(self, connection: sqlite3.Connection) -> list[sqlite3.Row]:
        return connection.execute(
            """
            SELECT DISTINCT t.category_id, c.name
            FROM trend_snapshots t
            LEFT JOIN category_snapshots c ON c.category_id=t.category_id
            WHERE t.category_id != ''
            ORDER BY COALESCE(c.name, t.category_id), t.category_id
            """
        ).fetchall()


class ProductRepository:
    def list(
        self, connection: sqlite3.Connection, *, cursor: int, limit: int, source_code: str | None,
        category_id: str | None, query: str | None, captured_from: str | None = None,
        captured_to: str | None = None
    ) -> Page:
        filters = "WHERE p.product_snapshot_id > ?"
        params: list[object] = [cursor]
        if source_code is not None:
            filters += " AND s.code = ?"
            params.append(source_code)
        if category_id is not None:
            filters += " AND p.ranking_category_id = ?"
            params.append(category_id)
        if query is not None:
            filters += " AND (CASEFOLD(p.product_id) LIKE ? OR CASEFOLD(coalesce(p.name, '')) LIKE ? OR CASEFOLD(coalesce(p.brand, '')) LIKE ? OR CASEFOLD(coalesce(p.domain_id, '')) LIKE ?)"
            term = f"%{query.casefold()}%"
            params.extend((term, term, term, term))
        if captured_from is not None:
            filters += " AND p.captured_at_utc >= ?"
            params.append(captured_from)
        if captured_to is not None:
            filters += " AND p.captured_at_utc <= ?"
            params.append(captured_to)
        return _page(
            connection,
            f"""
            SELECT p.product_snapshot_id AS row_id, s.code AS source_code, p.product_id, p.name,
                   p.brand, p.domain_id, p.ranking_category_id, p.highlight_position, p.captured_at_utc,
                   p.raw_source_id
            FROM product_snapshots p JOIN sources s ON s.source_id = p.source_id
            {filters} ORDER BY p.product_snapshot_id ASC LIMIT ?
            """,
            tuple(params),
            limit,
        )

    def detail(self, connection: sqlite3.Connection, product_id: str) -> dict[str, object] | None:
        row = connection.execute(
            """
            SELECT p.product_snapshot_id AS row_id, s.code AS source_code, p.product_id, p.name, p.brand, p.domain_id,
                   p.ranking_category_id, p.highlight_position, p.captured_at_utc, p.raw_source_id,
                   (SELECT COUNT(*) FROM offer_snapshots o WHERE o.product_id=p.product_id) AS offer_count,
                   (SELECT MIN(price) FROM offer_snapshots o WHERE o.product_id=p.product_id) AS lowest_price,
                   (SELECT MAX(price) FROM offer_snapshots o WHERE o.product_id=p.product_id) AS highest_price,
                   (SELECT COUNT(*) FROM visit_snapshots v JOIN offer_snapshots o ON o.item_id=v.item_id WHERE o.product_id=p.product_id) AS visit_points,
                   (SELECT COUNT(*) FROM keyword_product_mappings k WHERE k.product_id=p.product_id) AS related_keyword_count
            FROM product_snapshots p JOIN sources s ON s.source_id=p.source_id WHERE p.product_id=?
            ORDER BY p.captured_at_utc DESC LIMIT 1
            """, (product_id,)
        ).fetchone()
        if row is None:
            return None
        product = dict(row)
        product["snapshots"] = [dict(snapshot) for snapshot in connection.execute(
            """SELECT name, brand, domain_id, ranking_category_id, highlight_position, captured_at_utc, raw_source_id
               FROM product_snapshots WHERE product_id=? ORDER BY captured_at_utc DESC, product_snapshot_id DESC""", (product_id,)
        )]
        product["offers"] = [dict(offer) for offer in connection.execute(
            """SELECT item_id, seller_id, category_id, price, original_price, currency_id, condition,
                      CAST(free_shipping AS INTEGER) AS free_shipping, captured_at_utc, raw_source_id
               FROM offer_snapshots WHERE product_id=? ORDER BY captured_at_utc DESC, price ASC, item_id ASC""", (product_id,)
        )]
        product["visits"] = [dict(visit) for visit in connection.execute(
            """SELECT v.item_id, v.date_utc, v.visits, v.window_days, v.captured_at_utc, v.raw_source_id
               FROM visit_snapshots v JOIN offer_snapshots o ON o.item_id=v.item_id
               WHERE o.product_id=? ORDER BY v.date_utc DESC, v.item_id ASC""", (product_id,)
        )]
        product["keywords"] = [dict(keyword) for keyword in connection.execute(
            """SELECT keyword, scope, NULLIF(category_id, '') AS category_id, trend_position, relevance_position,
                      captured_at_utc, raw_source_id FROM keyword_product_mappings
               WHERE product_id=? ORDER BY captured_at_utc DESC, relevance_position ASC, keyword ASC""", (product_id,)
        )]
        categories = []
        for category in connection.execute(
            """SELECT ranking_category_id, offer_category_id, offer_category_name, path_json, offer_count,
                      captured_at_utc, raw_source_id FROM product_category_snapshots
               WHERE product_id=? ORDER BY captured_at_utc DESC""", (product_id,)
        ):
            entry = dict(category)
            entry["path"] = json.loads(entry.pop("path_json"))
            categories.append(entry)
        product["categories"] = categories
        return product


class RawSourceRepository:
    def get(self, connection: sqlite3.Connection, raw_source_id: int) -> sqlite3.Row | None:
        return connection.execute(
            """SELECT r.raw_source_id, s.code AS source_code, r.endpoint, r.captured_at_utc,
                      r.http_status, r.sha256, r.relative_path
               FROM raw_sources r JOIN sources s ON s.source_id=r.source_id WHERE r.raw_source_id=?""",
            (raw_source_id,),
        ).fetchone()


class JobRepository:
    def list(self, connection: sqlite3.Connection) -> list[sqlite3.Row]:
        return connection.execute("SELECT * FROM jobs ORDER BY created_at_utc DESC LIMIT 100").fetchall()

    def get(self, connection: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return cast(sqlite3.Row | None, row)

    def events(self, connection: sqlite3.Connection, job_id: str) -> list[sqlite3.Row]:
        return connection.execute("SELECT sequence,event_code,level,step_code,message,progress_current,progress_total,occurred_at_utc FROM job_events WHERE job_id=? ORDER BY sequence", (job_id,)).fetchall()
