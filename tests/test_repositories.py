import tempfile
from pathlib import Path

from app.repositories import ProductRepository, SourceRepository, TrendRepository
from meli.database import connect, initialize


def test_read_repositories_page_analytical_rows() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        database_path = Path(temporary) / "product_radar.sqlite3"
        connection = connect(database_path)
        try:
            initialize(connection)
            source_id = connection.execute("SELECT source_id FROM sources").fetchone()[0]
            connection.execute(
                """
                INSERT INTO raw_sources
                (source_id, relative_path, endpoint, captured_at_utc, sha256, ingested_at_utc)
                VALUES (?, 'data/raw/sample.json', '/trends/MLC', '2026-09-17T00:00:00Z', 'abc',
                        '2026-09-17T00:00:00Z')
                """,
                (source_id,),
            )
            raw_source_id = connection.execute("SELECT raw_source_id FROM raw_sources").fetchone()[0]
            connection.execute(
                """
                INSERT INTO trend_snapshots
                (source_id, site_id, scope, category_id, position, keyword, captured_at_utc, raw_source_id)
                VALUES (?, 'MLC', 'general', '', 1, 'muestra', '2026-09-17T00:00:00Z', ?)
                """,
                (source_id, raw_source_id),
            )
            connection.execute(
                """INSERT INTO trend_snapshots
                (source_id, site_id, scope, category_id, position, keyword, captured_at_utc, raw_source_id)
                VALUES (?, 'MLC', 'general', '', 2, 'Ñandú', '2026-09-18T00:00:00Z', ?)""",
                (source_id, raw_source_id),
            )
            connection.execute(
                """
                INSERT INTO product_snapshots
                (source_id, product_id, name, captured_at_utc, raw_source_id)
                VALUES (?, 'MLC1', 'Producto muestra', '2026-09-17T00:00:00Z', ?)
                """,
                (source_id, raw_source_id),
            )
            connection.commit()

            assert SourceRepository().list(connection)[0]["code"] == "mercado_libre"
            trends = TrendRepository().list(connection, cursor=0, limit=1, source_code="mercado_libre", scope="general", category_id=None, keyword="muestra")
            products = ProductRepository().list(connection, cursor=0, limit=1, source_code=None, category_id=None, query="producto")
            assert trends.rows[0]["keyword"] == "muestra"
            assert products.rows[0]["product_id"] == "MLC1"
            assert trends.next_cursor is None
            unicode_trends = TrendRepository().list(connection, cursor=0, limit=10, source_code=None, scope=None, category_id=None, keyword="ñandú")
            assert unicode_trends.rows[0]["keyword"] == "Ñandú"
        finally:
            connection.close()
