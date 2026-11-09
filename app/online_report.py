"""Build the historical 32-category report from a fresh Mercado Libre run.

The legacy collectors are reused inside a disposable workspace.  This keeps the
report structure stable while deliberately not adding the run to persistent RAW
storage; RAW retention is a separate operational decision.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.config import AppSettings
from app.database import database_connection
from meli.client import MercadoLibreClient
from meli.keyword_config import PRIORITY_KEYWORDS
from meli.oauth import refresh_access_token
from meli.report_config import OFFERS_PAGE_SIZE, REPORT_CATEGORIES
from meli.storage import save_json


@contextmanager
def _working_directory(path: Path):
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def refresh_worker_token(settings: AppSettings) -> None:
    """Rotate and persist the token pair in ignored runtime storage."""
    token_path = settings.backups_root / ".meli_oauth_tokens.json"
    refresh_token = None
    if token_path.is_file():
        refresh_token = json.loads(token_path.read_text(encoding="utf-8")).get("refresh_token")
    tokens = refresh_access_token(refresh_token)
    os.environ["MELI_ACCESS_TOKEN"] = tokens["access_token"]
    os.environ["MELI_REFRESH_TOKEN"] = tokens["refresh_token"]
    settings.backups_root.mkdir(parents=True, exist_ok=True)
    temporary = token_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"refresh_token": tokens["refresh_token"]}), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(token_path)


def generate_online_report(settings: AppSettings) -> Path:
    """Fetch live MLC data, retain its evidence, ingest it, then write the report."""
    refresh_worker_token(settings)
    with tempfile.TemporaryDirectory(prefix="product-radar-online-report-") as temporary:
        workspace = Path(temporary)
        with _working_directory(workspace):
            # Ordering mirrors the former capture workflow; downstream steps read
            # only artifacts from this disposable run.
            collectors = (
                "examples.03_trends",
                "examples.05_category_trends",
                "examples.06_highlights",
                "examples.09_catalog_coverage",
                "examples.12_keyword_products",
                "examples.14_category_hierarchy",
            )
            for module_name in collectors:
                importlib.import_module(module_name).main()
            raw_files = [str(path.relative_to(workspace)) for path in sorted((workspace / "data/raw").rglob("*.json"))]
            save_json({
                "site_id": os.getenv("MELI_SITE_ID", "MLC"),
                "started_at_utc": datetime.now(UTC).isoformat(),
                "finished_at_utc": datetime.now(UTC).isoformat(),
                "modules": list(collectors),
                "raw_files": raw_files,
                "raw_file_count": len(raw_files),
                "retention": "temporary_online_report",
            }, "data/raw/capture_runs", "capture_run_mlc")
            importlib.import_module("examples.13_generate_report").main()
            generated = sorted((workspace / "reports").glob("product_radar_MLC_*_32_categorias_online.md"))
            if not generated:
                raise RuntimeError("El generador no produjo el informe de 32 categorías.")
            settings.reports_root.mkdir(parents=True, exist_ok=True)
            destination = settings.reports_root / generated[-1].name
            shutil.copy2(generated[-1], destination)
            # The report is now a committed capture: retain its evidence before
            # the temporary workspace disappears, then use the established,
            # idempotent importer to project it into SQLite.
            shutil.copytree(workspace / "data" / "raw", settings.raw_root, dirs_exist_ok=True)
        importlib.import_module("examples.16_ingest_raw_to_sqlite").main()
        return destination


def _persist_raw(workspace: Path, settings: AppSettings, modules: list[str]) -> None:
    raw_files = [str(path.relative_to(workspace)) for path in sorted((workspace / "data/raw").rglob("*.json"))]
    save_json({"site_id": "MLC", "started_at_utc": datetime.now(UTC).isoformat(), "finished_at_utc": datetime.now(UTC).isoformat(), "modules": modules, "raw_files": raw_files, "raw_file_count": len(raw_files)}, "data/raw/capture_runs", "capture_run_mlc")
    shutil.copytree(workspace / "data/raw", settings.raw_root, dirs_exist_ok=True)


def _write_daily_report(workspace: Path, settings: AppSettings, suffix: str, title: str, lines: list[str]) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report = workspace / "reports" / f"product_radar_MLC_{timestamp}_{suffix}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join([f"# {title}", "", f"- Generado: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}", "- Fuente: Mercado Libre Chile (`MLC`).", "- Esta actualización no incluye tendencias semanales ni estima ventas.", "", *lines, ""]), encoding="utf-8")
    settings.reports_root.mkdir(parents=True, exist_ok=True)
    destination = settings.reports_root / report.name
    shutil.copy2(report, destination)
    return destination


def update_daily_highlights(settings: AppSettings) -> Path:
    """Refresh the 32 category rankings; this is intentionally light-weight."""
    refresh_worker_token(settings)
    with tempfile.TemporaryDirectory(prefix="product-radar-daily-highlights-") as temporary:
        workspace = Path(temporary)
        with _working_directory(workspace):
            client = MercadoLibreClient(site_id="MLC")
            summary = []
            for category_id, category_name in REPORT_CATEGORIES.items():
                response = client.get_response(f"/highlights/{client.site_id}/category/{category_id}")
                try: payload = response.json()
                except ValueError: payload = {"text": response.text[:2000]}
                save_json(payload, "data/raw/highlights", f"highlights_{client.site_id.lower()}_{category_id.lower()}")
                content = payload.get("content", []) if isinstance(payload, dict) else []
                first = content[0] if content else {}
                summary.append(f"| {category_name} | {category_id} | {len(content)} | #{first.get('position', '—')} {first.get('id', 'Sin resultados')} ({first.get('type', '—')}) |")
            _persist_raw(workspace, settings, ["daily_highlights"])
            report = _write_daily_report(workspace, settings, "daily_rankings", "Product Radar — Rankings diarios", ["## Cobertura", "", "| Categoría | ID | Resultados | Primer lugar observado |", "|---|---|---:|---|", *summary])
        importlib.import_module("examples.16_ingest_raw_to_sqlite").main()
        return report


def update_daily_catalog(settings: AppSettings, limit: int = 12) -> Path:
    """Refresh detail, first offers page and visits for persisted priority products."""
    refresh_worker_token(settings)
    with database_connection(settings.database_path) as connection:
        candidates = connection.execute("""SELECT product_id, ranking_category_id, highlight_position FROM product_snapshots
            GROUP BY product_id ORDER BY MAX(captured_at_utc) DESC, highlight_position ASC LIMIT ?""", (limit,)).fetchall()
    with tempfile.TemporaryDirectory(prefix="product-radar-daily-catalog-") as temporary:
        workspace = Path(temporary)
        with _working_directory(workspace):
            client, products = MercadoLibreClient(site_id="MLC"), []
            for candidate in candidates:
                product_id = candidate["product_id"]
                detail_response = client.get_response(f"/products/{product_id}")
                detail = detail_response.json() if detail_response.ok else {}
                save_json(detail, "data/raw/catalog_coverage/products", f"product_{product_id.lower()}")
                offers_response = client.get_response(f"/products/{product_id}/items", params={"limit": OFFERS_PAGE_SIZE, "offset": 0})
                offers = offers_response.json() if offers_response.ok else {"results": [], "paging": {}}
                save_json(offers, "data/raw/catalog_coverage/offers", f"offers_{product_id.lower()}")
                row = {"product_id": product_id, "category_id": candidate["ranking_category_id"], "category_name": REPORT_CATEGORIES.get(candidate["ranking_category_id"], candidate["ranking_category_id"]), "highlight_position": candidate["highlight_position"], "name": detail.get("name"), "domain_id": detail.get("domain_id"), "status": detail.get("status"), "product_http_status": detail_response.status_code, "offers_http_status": offers_response.status_code, "offer_total": (offers.get("paging") or {}).get("total")}
                results = offers.get("results") or []
                if results:
                    item_id = results[0].get("item_id")
                    if item_id:
                        visits_response = client.get_response(f"/items/{item_id}/visits/time_window", params={"last": 30, "unit": "day"})
                        visits = visits_response.json() if visits_response.ok else {"results": []}
                        save_json(visits, "data/raw/catalog_coverage/visits", f"visits_{item_id.lower()}")
                        row["visit_sample"] = {"item_id": item_id, "http_status": visits_response.status_code, "total_visits_30d": visits.get("total_visits")}
                products.append(row)
            save_json({"summary": {"visit_samples": [row["visit_sample"] for row in products if row.get("visit_sample")]}, "products": products}, "data/raw/catalog_coverage", "catalog_coverage_report")
            _persist_raw(workspace, settings, ["daily_catalog"])
            rows = [f"| {row['product_id']} | {row.get('name') or '—'} | {row.get('category_name') or '—'} | {row.get('offer_total') if row.get('offer_total') is not None else '—'} | {(row.get('visit_sample') or {}).get('total_visits_30d', '—')} |" for row in products]
            report = _write_daily_report(workspace, settings, "daily_catalog", "Product Radar — Catálogo y visitas diarios", ["## Muestra priorizada", "", "| Producto | Nombre | Categoría | Ofertas reportadas | Visitas 30 días de ítem muestra |", "|---|---|---|---:|---:|", *rows, "", "Las visitas son tráfico observado de un ítem representativo; no son ventas."])
        importlib.import_module("examples.16_ingest_raw_to_sqlite").main()
        return report


def _latest_offer_rows(settings: AppSettings, limit: int) -> list[dict[str, object]]:
    with database_connection(settings.database_path) as connection:
        rows = connection.execute("""SELECT product_id, item_id, seller_id, price, free_shipping
            FROM offer_snapshots WHERE seller_id != ''
            GROUP BY product_id, item_id ORDER BY captured_at_utc DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(row) for row in rows]


def _enrichment_report(workspace: Path, settings: AppSettings, scope: str, lines: list[str]) -> Path:
    _persist_raw(workspace, settings, [scope])
    return _write_daily_report(workspace, settings, scope, f"Product Radar — {scope.replace('_', ' ').title()}", lines)


def run_enrichment_capture(settings: AppSettings, scope: str) -> Path:
    """Run one bounded enrichment package; calls share MercadoLibreClient's rate budget."""
    refresh_worker_token(settings)
    with tempfile.TemporaryDirectory(prefix=f"product-radar-{scope}-") as temporary:
        workspace = Path(temporary)
        with _working_directory(workspace):
            client = MercadoLibreClient(site_id="MLC")
            if scope == "sellers":
                sellers = []
                seen: set[str] = set()
                for offer in _latest_offer_rows(settings, settings.enrichment_seller_limit * 3):
                    seller_id = str(offer["seller_id"])
                    if seller_id in seen: continue
                    seen.add(seller_id)
                    response = client.get_response(f"/users/{seller_id}")
                    payload = response.json() if response.ok or response.status_code == 206 else {"error": response.text[:500]}
                    save_json({"seller_id": seller_id, "http_status": response.status_code, "profile": payload}, "data/raw/sellers", f"seller_{seller_id}")
                    sellers.append((seller_id, response.status_code))
                    if len(sellers) >= settings.enrichment_seller_limit: break
                report = _enrichment_report(workspace, settings, scope, ["## Cobertura", "", f"- Vendedores únicos consultados: {len(sellers)}", "- Incluye perfiles públicos; una respuesta 206 se conserva como contenido parcial."])
            elif scope == "expanded_visits":
                selected: dict[str, list[dict[str, object]]] = {}
                for offer in _latest_offer_rows(settings, 500):
                    selected.setdefault(str(offer["product_id"]), []).append(offer)
                total = 0
                for product_id, offers in selected.items():
                    ordered = sorted(offers, key=lambda row: float(row["price"] or 0))
                    candidates = [ordered[0], ordered[len(ordered) // 2], ordered[-1]]
                    candidates += [row for row in ordered if row["free_shipping"]][:1]
                    unique = {str(row["item_id"]): row for row in candidates}
                    for reason, row in zip(("lowest_price", "median_price", "highest_price", "free_shipping"), unique.values()):
                        if total >= 100: break
                        item_id = str(row["item_id"]); response = client.get_response(f"/items/{item_id}/visits/time_window", params={"last": 30, "unit": "day"})
                        payload = response.json() if response.ok else {"results": [], "error": response.text[:500]}
                        save_json({"product_id": product_id, "item_id": item_id, "selection_reason": reason, "http_status": response.status_code, "visits": payload}, "data/raw/expanded_visits", f"visits_{item_id}")
                        total += 1
                report = _enrichment_report(workspace, settings, scope, ["## Muestra ampliada", "", f"- Ítems consultados: {total}", "- Las visitas representan tráfico observado, no ventas."])
            elif scope == "keyword_supply":
                keywords = PRIORITY_KEYWORDS[:settings.enrichment_keyword_limit]
                categories: dict[str, str] = {}
                summary = []
                for entry in keywords:
                    keyword, portfolio = entry["keyword"], entry["portfolio"]
                    supply = client.get_response("/products/search", params={"status": "active", "site_id": "MLC", "q": keyword, "limit": 50})
                    domains = client.get_response("/sites/MLC/domain_discovery/search", params={"q": keyword, "limit": 3})
                    supply_data = supply.json() if supply.ok else {"results": [], "error": supply.text[:500]}
                    domain_data = domains.json() if domains.ok else {"error": domains.text[:500]}
                    save_json({"keyword": keyword, "portfolio": portfolio, "selection_source": "manual_priority_portfolio", "supply_http_status": supply.status_code, "domain_http_status": domains.status_code, "supply": supply_data, "domains": domain_data}, "data/raw/keyword_supply", f"keyword_supply_{keyword.lower().replace(' ', '_')[:50]}")
                    predicted = []
                    for item in domain_data if isinstance(domain_data, list) else []:
                        category_id = item.get("category_id")
                        if category_id:
                            categories[category_id] = item.get("category_name") or category_id
                            predicted.append(item.get("category_name") or category_id)
                    total = (supply_data.get("paging") or {}).get("total", len(supply_data.get("results") or [])) if isinstance(supply_data, dict) else 0
                    summary.append(f"| {portfolio} | {keyword} | {total} | {', '.join(predicted) or 'Sin predicción'} |")
                for category_id in sorted(categories):
                    response = client.get_response(f"/categories/{category_id}/attributes")
                    save_json({"category_id": category_id, "http_status": response.status_code, "attributes": response.json() if response.ok else []}, "data/raw/category_attributes", f"attributes_{category_id.lower()}")
                category_lines = [f"| {category_id} | {name} |" for category_id, name in sorted(categories.items())]
                report = _enrichment_report(workspace, settings, scope, ["## Oferta observable por keyword", "", "- Origen de selección: portafolio manual prioritario.", "- El total refleja la oferta observable reportada por la API; no representa ventas.", "", "| Portafolio | Keyword | Oferta observable | Categorías predichas por Mercado Libre |", "|---|---|---:|---|", *summary, "", "## Categorías consultadas para atributos", "", "Estas categorías son predicciones taxonómicas de Mercado Libre para las keywords anteriores; no son necesariamente las 32 categorías del informe semanal.", "", "| ID Mercado Libre | Categoría predicha |", "|---|---|", *category_lines])
            elif scope == "shipping":
                destinations = [zip_code.strip() for zip_code in settings.enrichment_destination_zip_codes.split(",") if zip_code.strip()]
                items = _latest_offer_rows(settings, settings.enrichment_shipping_item_limit)
                total = 0
                for offer in items:
                    for zip_code in destinations:
                        item_id = str(offer["item_id"]); response = client.get_response(f"/items/{item_id}/shipping_options", params={"zip_code": zip_code})
                        save_json({"item_id": item_id, "destination_code": zip_code, "http_status": response.status_code, "options": response.json() if response.ok else {"error": response.text[:500]}}, "data/raw/shipping_options", f"shipping_{item_id.lower()}_{zip_code}")
                        total += 1
                report = _enrichment_report(workspace, settings, scope, ["## Simulación logística", "", f"- Consultas ítem-destino: {total}", f"- Destinos configurados: {', '.join(destinations) or 'ninguno'}", "- Costos y plazos dependen del destino y condiciones de la simulación; no son universales."])
            else:
                raise ValueError(f"Paquete de enriquecimiento desconocido: {scope}")
        importlib.import_module("examples.16_ingest_raw_to_sqlite").main()
        return report
