import unittest
from importlib import import_module

trend_rows = import_module("examples.16_ingest_raw_to_sqlite").trend_rows


class TrendRowsTests(unittest.TestCase):
    def test_returns_mapping_rows_from_list(self) -> None:
        rows = [{"keyword": "uno"}, {"keyword": "dos"}]

        self.assertEqual(trend_rows(rows), rows)

    def test_ignores_api_error_payload(self) -> None:
        payload = {"error": "not_found", "message": "not available", "status": 404}

        self.assertEqual(trend_rows(payload), [])

    def test_ignores_malformed_entries_inside_list(self) -> None:
        self.assertEqual(trend_rows([{"keyword": "válido"}, "inválido"]), [{"keyword": "válido"}])


if __name__ == "__main__":
    unittest.main()
