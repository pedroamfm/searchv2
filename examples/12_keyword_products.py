import hashlib
import json
import re
import unicodedata
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.report_config import REPORT_CATEGORIES
from meli.storage import save_json


CATEGORIES = REPORT_CATEGORIES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cruza keywords de tendencias con productos de catálogo.")
    parser.add_argument("category_ids", nargs="*", help="Categorías a procesar; por defecto todas.")
    parser.add_argument(
        "--append-previous",
        action="store_true",
        help="Conserva el último mapa y agrega sólo las categorías indicadas.",
    )
    return parser.parse_args()


def latest(pattern: str) -> Path:
    files = sorted(Path().glob(pattern))
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos para {pattern}")
    return files[-1]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_keyword(keyword: str) -> str:
    normalized = unicodedata.normalize("NFKD", keyword).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")[:48]
    digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()[:8]
    return f"{slug or 'keyword'}_{digest}"


def brand_from(product: dict[str, Any]) -> str | None:
    for attribute in product.get("attributes", []):
        if attribute.get("id") == "BRAND":
            return attribute.get("value_name")
    return None


def main() -> None:
    load_dotenv()
    args = parse_args()
    client = MercadoLibreClient()
    selected: list[dict[str, Any]] = []
    selected_categories = (
        {category_id: CATEGORIES[category_id] for category_id in args.category_ids}
        if args.category_ids
        else CATEGORIES
    )

    if not args.append_previous:
        general_file = latest("data/raw/trends/trends_mlc_*.json")
        for position, trend in enumerate(load_json(general_file)[:10], start=1):
            selected.append(
                {
                    "scope": "general",
                    "category_id": None,
                    "category_name": None,
                    "trend_position": position,
                    "keyword": trend["keyword"],
                    "trend_raw_file": str(general_file),
                }
            )

    for category_id, category_name in selected_categories.items():
        trend_file = latest(
            f"data/raw/trends/categories/trends_mlc_{category_id.lower()}_*.json"
        )
        category_trends = load_json(trend_file)
        if not isinstance(category_trends, list):
            print(f"Sin tendencias disponibles para {category_name}; se omite cruce de keywords")
            continue
        for position, trend in enumerate(category_trends[:3], start=1):
            selected.append(
                {
                    "scope": "category",
                    "category_id": category_id,
                    "category_name": category_name,
                    "trend_position": position,
                    "keyword": trend["keyword"],
                    "trend_raw_file": str(trend_file),
                }
            )

    captured_at = datetime.now(timezone.utc).isoformat()
    mappings: list[dict[str, Any]] = []
    if args.append_previous:
        previous_file = latest("data/raw/keyword_products/keyword_product_map_mlc_*.json")
        mappings = load_json(previous_file).get("mappings", [])
        selected_ids = set(selected_categories)
        mappings = [row for row in mappings if row.get("category_id") not in selected_ids]
    for candidate in selected:
        keyword = candidate["keyword"]
        response = client.get(
            "/products/search",
            params={
                "status": "active",
                "site_id": client.site_id,
                "q": keyword,
                "limit": 10,
            },
        )
        raw_file = save_json(
            response,
            "data/raw/keyword_products/searches",
            f"search_{candidate['scope']}_{candidate['category_id'] or 'mlc'}_"
            f"{safe_keyword(keyword)}",
        )
        products = []
        for relevance_position, product in enumerate(response.get("results", []), start=1):
            products.append(
                {
                    "relevance_position": relevance_position,
                    "product_id": product.get("id"),
                    "name": product.get("name"),
                    "brand": brand_from(product),
                    "domain_id": product.get("domain_id"),
                    "status": product.get("status"),
                }
            )
        mappings.append(
            {
                **candidate,
                "captured_at_utc": captured_at,
                "search_total_reported": (response.get("paging") or {}).get("total"),
                "results_returned": len(products),
                "products": products,
                "raw_file": str(raw_file),
            }
        )
        print(f"{candidate['scope']} {candidate['trend_position']}: {keyword} -> {len(products)}")

    output = save_json(
        {
            "captured_at_utc": captured_at,
            "site_id": client.site_id,
            "selection": {"general_limit": 10, "category_limit": 3},
            "mappings": mappings,
        },
        "data/raw/keyword_products",
        "keyword_product_map_mlc",
    )
    print(f"Mapa keyword-producto: {output}")


if __name__ == "__main__":
    main()
