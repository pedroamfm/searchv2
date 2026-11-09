import json
import statistics
import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.report_config import (
    MAX_OFFERS_PER_PRODUCT,
    OFFERS_PAGE_SIZE,
    REPORT_CATEGORIES,
)
from meli.storage import save_json


CATEGORIES = REPORT_CATEGORIES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura cobertura de catálogo por categoría.")
    parser.add_argument("category_ids", nargs="*", help="Categorías a capturar; por defecto todas.")
    parser.add_argument(
        "--append-previous",
        action="store_true",
        help="Conserva productos del último reporte para completar una captura por bloques.",
    )
    return parser.parse_args()


def latest_highlight_file(category_id: str) -> Path:
    pattern = f"highlights_mlc_{category_id.lower()}_*.json"
    files = sorted(Path("data/raw/highlights").glob(pattern))
    if not files:
        raise FileNotFoundError(f"No hay highlights para {category_id}")
    return files[-1]


def top_products(category_id: str, limit: int = 3) -> list[dict[str, Any]]:
    data = json.loads(latest_highlight_file(category_id).read_text(encoding="utf-8"))
    products = [row for row in data.get("content", []) if row.get("type") == "PRODUCT"]
    return products[:limit]


def body(response: Any) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"text": response.text[:2000]}


def brand_from(product: dict[str, Any]) -> str | None:
    for attribute in product.get("attributes", []):
        if attribute.get("id") == "BRAND":
            return attribute.get("value_name")
    return None


def fetch_offers(
    client: MercadoLibreClient,
    product_id: str,
    output: Path,
) -> tuple[int, dict[str, Any]]:
    results: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None
    status = 0
    pages = 0

    while offset < MAX_OFFERS_PER_PRODUCT and (total is None or offset < total):
        response = client.get_response(
            f"/products/{product_id}/items",
            params={"limit": OFFERS_PAGE_SIZE, "offset": offset},
        )
        status = response.status_code
        page = body(response)
        save_json(
            page,
            output / "offers" / "pages",
            f"offers_{product_id.lower()}_offset_{offset}",
        )
        if not response.ok or not isinstance(page, dict):
            break
        page_results = page.get("results") or []
        total = (page.get("paging") or {}).get("total", len(page_results))
        results.extend(page_results)
        pages += 1
        if not page_results:
            break
        offset += len(page_results)

    combined = {
        "paging": {
            "total": total,
            "offset": 0,
            "limit": OFFERS_PAGE_SIZE,
        },
        "results": results,
        "collection": {
            "pages": pages,
            "complete": total is not None and len(results) >= total,
            "max_offers_safety_limit": MAX_OFFERS_PER_PRODUCT,
        },
    }
    save_json(combined, output / "offers", f"offers_{product_id.lower()}")
    return status, combined


def main() -> None:
    load_dotenv()
    args = parse_args()
    client = MercadoLibreClient()
    output = Path("data/raw/catalog_coverage")
    selected_categories = (
        {category_id: CATEGORIES[category_id] for category_id in args.category_ids}
        if args.category_ids
        else CATEGORIES
    )
    report: list[dict[str, Any]] = []
    if args.append_previous:
        previous_files = sorted(output.glob("catalog_coverage_report_*.json"))
        if not previous_files:
            raise FileNotFoundError("No hay un reporte previo para complementar")
        report = json.loads(previous_files[-1].read_text(encoding="utf-8")).get("products", [])
        selected_ids = set(selected_categories)
        report = [row for row in report if row.get("category_id") not in selected_ids]

    for category_id, category_name in selected_categories.items():
        visit_sample_done = False
        for ranked in top_products(category_id):
            product_id = ranked["id"]
            row: dict[str, Any] = {
                "category_id": category_id,
                "category_name": category_name,
                "highlight_position": ranked.get("position"),
                "product_id": product_id,
                # Keep a stable schema when a downstream product or offers
                # endpoint is temporarily unavailable.  The HTTP status below
                # records the failure; null metrics are valid observations.
                "name": None,
                "offer_total": None,
                "offers_returned": 0,
                "seller_count_returned": 0,
                "min_price_returned": None,
                "max_price_returned": None,
                "mean_price_returned": None,
                "median_price_returned": None,
                "offers_collection_complete": False,
            }

            detail_response = client.get_response(f"/products/{product_id}")
            detail = body(detail_response)
            save_json(detail, output / "products", f"product_{product_id.lower()}")
            row["product_http_status"] = detail_response.status_code
            if detail_response.ok and isinstance(detail, dict):
                row.update(
                    {
                        "name": detail.get("name"),
                        "brand": brand_from(detail),
                        "domain_id": detail.get("domain_id"),
                        "status": detail.get("status"),
                        "attribute_count": len(detail.get("attributes", [])),
                        "has_buy_box_winner": bool(detail.get("buy_box_winner")),
                        "has_sold_quantity": "sold_quantity" in detail,
                        "sold_quantity": detail.get("sold_quantity"),
                    }
                )

            offers_status, offers = fetch_offers(client, product_id, output)
            row["offers_http_status"] = offers_status
            if 200 <= offers_status < 300:
                results = offers.get("results") or []
                prices = [offer["price"] for offer in results if offer.get("price") is not None]
                row.update(
                    {
                        "offer_total": (offers.get("paging") or {}).get("total"),
                        "offers_returned": len(results),
                        "seller_count_returned": len(
                            {offer.get("seller_id") for offer in results if offer.get("seller_id")}
                        ),
                        "min_price_returned": min(prices) if prices else None,
                        "max_price_returned": max(prices) if prices else None,
                        "mean_price_returned": statistics.fmean(prices) if prices else None,
                        "median_price_returned": statistics.median(prices) if prices else None,
                        "currency_id": next(
                            (offer.get("currency_id") for offer in results if offer.get("currency_id")),
                            None,
                        ),
                        "offers_have_sold_quantity": any(
                            "sold_quantity" in offer for offer in results
                        ),
                        "offers_have_available_quantity": any(
                            "available_quantity" in offer for offer in results
                        ),
                        "offers_collection_complete": (offers.get("collection") or {}).get(
                            "complete", False
                        ),
                    }
                )

                if results and not visit_sample_done:
                    item_id = results[0].get("item_id")
                    if item_id:
                        visits_response = client.get_response(
                            f"/items/{item_id}/visits/time_window",
                            params={"last": 30, "unit": "day"},
                        )
                        visits = body(visits_response)
                        save_json(
                            visits,
                            output / "visits",
                            f"visits_{item_id.lower()}",
                        )
                        row["visit_sample"] = {
                            "item_id": item_id,
                            "http_status": visits_response.status_code,
                            "total_visits_30d": (
                                visits.get("total_visits")
                                if isinstance(visits, dict) and visits_response.ok
                                else None
                            ),
                        }
                        visit_sample_done = True

            report.append(row)
            print(
                f"{category_id} pos {ranked.get('position')}: {product_id} "
                f"product={row.get('product_http_status')} offers={row.get('offers_http_status')}"
            )

    summary = {
        "sample_size": len(report),
        "categories": len({row["category_id"] for row in report}),
        "product_statuses": dict(Counter(row["product_http_status"] for row in report)),
        "offer_statuses": dict(Counter(row["offers_http_status"] for row in report)),
        "products_with_name": sum(bool(row.get("name")) for row in report),
        "products_with_brand": sum(bool(row.get("brand")) for row in report),
        "products_with_buy_box_winner": sum(
            bool(row.get("has_buy_box_winner")) for row in report
        ),
        "products_with_offers": sum((row.get("offer_total") or 0) > 0 for row in report),
        "visit_samples": [row["visit_sample"] for row in report if row.get("visit_sample")],
    }
    report_file = save_json(
        {"summary": summary, "products": report},
        output,
        "catalog_coverage_report",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Reporte: {report_file}")


if __name__ == "__main__":
    main()
