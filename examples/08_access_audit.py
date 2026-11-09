import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.storage import save_json


PRODUCT_ID = "MLC75478520"
ITEM_ID = "MLC2771781042"
USER_PRODUCT_ID = "MLCU3515284776"


@dataclass(frozen=True)
class AuditCase:
    name: str
    endpoint: str
    params: dict[str, Any] | None = None
    scope: str = "public_or_market"


def parse_body(response: Any) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"text": response.text[:2000]}


def body_summary(body: Any) -> dict[str, Any]:
    if isinstance(body, list):
        return {"body_type": "list", "count": len(body)}
    if not isinstance(body, dict):
        return {"body_type": type(body).__name__}

    summary: dict[str, Any] = {
        "body_type": "object",
        "keys": sorted(body.keys()),
    }
    if isinstance(body.get("paging"), dict):
        summary["paging"] = {
            key: body["paging"].get(key)
            for key in ("total", "offset", "limit")
            if key in body["paging"]
        }
    if isinstance(body.get("results"), list):
        summary["results_count"] = len(body["results"])
    if isinstance(body.get("content"), list):
        summary["content_count"] = len(body["content"])
    if body.get("error"):
        summary["error"] = body.get("error")
        summary["message"] = body.get("message")
    return summary


def is_accessible(status_code: int, body: Any) -> bool:
    if not 200 <= status_code < 300:
        return False
    if isinstance(body, list):
        nested_statuses = [
            row.get("status_code")
            for row in body
            if isinstance(row, dict) and "status_code" in row
        ]
        if nested_statuses:
            return all(
                isinstance(nested, int) and 200 <= nested < 300
                for nested in nested_statuses
            )
    return True


def main() -> None:
    load_dotenv()
    client = MercadoLibreClient()
    me = client.get("/users/me")
    own_user_id = me["id"]

    cases = [
        AuditCase("site", f"/sites/{client.site_id}"),
        AuditCase("root_categories", f"/sites/{client.site_id}/categories"),
        AuditCase("category_detail", "/categories/MLC1051"),
        AuditCase("general_trends", f"/trends/{client.site_id}"),
        AuditCase("category_trends", f"/trends/{client.site_id}/MLC1051"),
        AuditCase(
            "category_highlights",
            f"/highlights/{client.site_id}/category/MLC1051",
        ),
        AuditCase(
            "product_search",
            "/products/search",
            {"status": "active", "site_id": client.site_id, "q": "lavadora pequeña"},
        ),
        AuditCase("product_detail", f"/products/{PRODUCT_ID}"),
        AuditCase("product_offers", f"/products/{PRODUCT_ID}/items"),
        AuditCase(
            "product_highlight_position",
            f"/highlights/{client.site_id}/product/{PRODUCT_ID}",
        ),
        AuditCase(
            "marketplace_search",
            f"/sites/{client.site_id}/search",
            {"q": "lavadora pequeña", "limit": 5},
        ),
        AuditCase("third_party_item", f"/items/{ITEM_ID}"),
        AuditCase("third_party_item_bulk", "/items/bulk", {"ids": ITEM_ID}),
        AuditCase("third_party_user_product", f"/user-products/{USER_PRODUCT_ID}"),
        AuditCase("third_party_item_total_visits", "/visits/items", {"ids": ITEM_ID}),
        AuditCase(
            "third_party_item_visit_window",
            f"/items/{ITEM_ID}/visits/time_window",
            {"last": 30, "unit": "day"},
        ),
        AuditCase(
            "own_items_search",
            f"/users/{own_user_id}/items/search",
            {"limit": 5},
            scope="authorized_user",
        ),
        AuditCase(
            "own_item_visits",
            f"/users/{own_user_id}/items_visits/time_window",
            {"last": 30, "unit": "day"},
            scope="authorized_user",
        ),
    ]

    report = []
    raw_directory = Path("data/raw/access_audit")
    for case in cases:
        response = client.get_response(case.endpoint, params=case.params)
        body = parse_body(response)
        raw_file = save_json(body, raw_directory, case.name)
        result = {
            "name": case.name,
            "endpoint": case.endpoint,
            "scope": case.scope,
            "http_status": response.status_code,
            "accessible": is_accessible(response.status_code, body),
            "summary": body_summary(body),
            "raw_file": str(raw_file),
        }
        report.append(result)
        print(
            f"{case.name}: HTTP {response.status_code} "
            f"({'accesible' if result['accessible'] else 'restringido/error'})"
        )

    report_file = save_json(report, raw_directory, "access_report")
    print(f"Reporte: {report_file}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
