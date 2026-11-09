import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.report_config import REPORT_CATEGORIES
from meli.storage import save_json


def latest(pattern: str) -> Path:
    files = sorted(Path().glob(pattern))
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos para {pattern}")
    return files[-1]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def body(response: Any) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"text": response.text[:2000]}


def main() -> None:
    load_dotenv()
    client = MercadoLibreClient()
    coverage_file = latest("data/raw/catalog_coverage/catalog_coverage_report_*.json")
    products = load(coverage_file)["products"]
    product_categories: list[dict[str, Any]] = []
    category_ids = set(REPORT_CATEGORIES)

    for product in products:
        offers_file = latest(
            f"data/raw/catalog_coverage/offers/offers_{product['product_id'].lower()}_*.json"
        )
        offers = load(offers_file).get("results", [])
        counts = Counter(
            offer.get("category_id") for offer in offers if offer.get("category_id")
        )
        category_ids.update(counts)
        product_categories.append(
            {
                "product_id": product["product_id"],
                "ranking_category_id": product["category_id"],
                "offer_category_counts": dict(counts),
                "primary_offer_category_id": counts.most_common(1)[0][0] if counts else None,
                "offers_raw_file": str(offers_file),
            }
        )

    categories: dict[str, dict[str, Any]] = {}
    for category_id in sorted(category_ids):
        response = client.get_response(f"/categories/{category_id}")
        payload = body(response)
        raw_file = save_json(
            payload,
            "data/raw/category_details",
            f"category_{category_id.lower()}",
        )
        categories[category_id] = {
            "http_status": response.status_code,
            "name": payload.get("name") if isinstance(payload, dict) else None,
            "total_items_in_this_category": (
                payload.get("total_items_in_this_category")
                if isinstance(payload, dict)
                else None
            ),
            "path_from_root": payload.get("path_from_root", []) if isinstance(payload, dict) else [],
            "children_categories": (
                payload.get("children_categories", []) if isinstance(payload, dict) else []
            ),
            "raw_file": str(raw_file),
        }
        print(f"{category_id}: HTTP {response.status_code}")

    for row in product_categories:
        detail = categories.get(row["primary_offer_category_id"], {})
        row["primary_category_name"] = detail.get("name")
        row["primary_category_path"] = detail.get("path_from_root", [])

    report = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "site_id": client.site_id,
        "coverage_raw_file": str(coverage_file),
        "selected_root_categories": REPORT_CATEGORIES,
        "categories": categories,
        "product_categories": product_categories,
    }
    output = save_json(
        report,
        "data/raw/category_details",
        "category_hierarchy_mlc",
    )
    print(f"Jerarquía de categorías: {output}")


if __name__ == "__main__":
    main()
