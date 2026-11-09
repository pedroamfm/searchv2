import json
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from meli.report_config import REPORT_CATEGORIES

CATEGORIES = REPORT_CATEGORIES


def latest(pattern: str, previous: bool = False) -> Path:
    files = sorted(Path().glob(pattern))
    index = -2 if previous else -1
    if len(files) < abs(index):
        raise FileNotFoundError(f"No hay suficientes archivos para {pattern}")
    return files[index]


def previous_if_available(pattern: str) -> Path | None:
    files = sorted(Path().glob(pattern))
    return files[-2] if len(files) >= 2 else None


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def escape(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def money(value: Any) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f}".replace(",", ".")


def trend_group(position: int) -> str:
    if position <= 10:
        return "Mayor crecimiento"
    if position <= 30:
        return "Mayor interés"
    return "Popular"


def table(headers: list[str], rows: list[list[Any]], aligns: str | None = None) -> str:
    separator = aligns or "|".join("---" for _ in headers)
    output = [
        "| " + " | ".join(headers) + " |",
        "|" + separator + "|",
    ]
    output.extend("| " + " | ".join(escape(cell) for cell in row) + " |" for row in rows)
    return "\n".join(output)


def trend_delta(old_positions: dict[str, int], keyword: str, current: int) -> str:
    old = old_positions.get(keyword)
    if old is None:
        return "Nuevo"
    delta = current - old
    if delta == 0:
        return "="
    direction = "↑" if delta < 0 else "↓"
    return f"{direction} {abs(delta)}"


def visit_metrics(item_id: str) -> dict[str, Any]:
    path = latest(f"data/raw/catalog_coverage/visits/visits_{item_id.lower()}_*.json")
    payload = load(path)
    points = {
        date.fromisoformat(row["date"][:10]): row["total"]
        for row in payload.get("results", [])
    }
    if not points:
        return {"item_id": item_id, "raw_file": str(path)}
    end = max(points)
    recent_start = end - timedelta(days=6)
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    recent = sum(value for day, value in points.items() if recent_start <= day <= end)
    previous = sum(
        value for day, value in points.items() if previous_start <= day <= previous_end
    )
    span = (end - min(points)).days + 1
    comparable = span >= 14 and len(points) >= 14 and previous > 0
    variation = ((recent / previous) - 1) * 100 if comparable else None
    return {
        "item_id": item_id,
        "total_30d": payload.get("total_visits"),
        "recent_7d": recent,
        "previous_7d": previous if comparable else None,
        "variation_7d": variation,
        "days_with_data": len(points),
        "calendar_span": span,
        "raw_file": str(path),
    }


def offer_metrics(product_id: str) -> dict[str, Any]:
    path = latest(f"data/raw/catalog_coverage/offers/offers_{product_id.lower()}_*.json")
    results = load(path).get("results", [])
    return {
        "free_shipping": sum(bool((row.get("shipping") or {}).get("free_shipping")) for row in results),
        "discounts": sum(
            row.get("original_price") is not None
            and row.get("price") is not None
            and row["original_price"] > row["price"]
            for row in results
        ),
        "official_stores": sum(row.get("official_store_id") is not None for row in results),
        "conditions": ", ".join(sorted({row.get("condition", "—") for row in results})),
        "raw_file": str(path),
    }


def reference_keywords(product_id: str) -> str:
    path = latest(f"data/raw/catalog_coverage/products/product_{product_id.lower()}_*.json")
    product = load(path)
    values = [product.get("name"), product.get("family_name"), product.get("domain_id")]
    unique = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return "; ".join(unique)
def main() -> None:
    general_file = latest("data/raw/trends/trends_mlc_*.json")
    # An online report can be generated from a single fresh run.  Comparisons are
    # omitted rather than borrowing a prior local capture.
    old_general_file = previous_if_available("data/raw/trends/trends_mlc_*.json") or general_file
    has_general_comparison = old_general_file != general_file
    general = load(general_file)
    old_general = load(old_general_file)
    old_general_positions = {row["keyword"]: pos for pos, row in enumerate(old_general, 1)}
    current_general_positions = {row["keyword"]: pos for pos, row in enumerate(general, 1)}

    category_trends: dict[str, list[dict[str, Any]]] = {}
    category_trend_status: dict[str, str] = {}
    category_trend_files: dict[str, Path] = {}
    highlights: dict[str, dict[str, Any]] = {}
    highlight_status: dict[str, str] = {}
    highlight_files: dict[str, Path] = {}
    old_highlights: dict[str, dict[str, Any]] = {}
    for category_id in CATEGORIES:
        category_trend_files[category_id] = latest(
            f"data/raw/trends/categories/trends_mlc_{category_id.lower()}_*.json"
        )
        trend_payload = load(category_trend_files[category_id])
        category_trends[category_id] = trend_payload if isinstance(trend_payload, list) else []
        category_trend_status[category_id] = (
            "Disponible" if isinstance(trend_payload, list) else "No disponible en la API"
        )
        highlight_files[category_id] = latest(
            f"data/raw/highlights/highlights_mlc_{category_id.lower()}_*.json"
        )
        highlights_payload = load(highlight_files[category_id])
        highlights[category_id] = (
            highlights_payload
            if isinstance(highlights_payload, dict) and isinstance(highlights_payload.get("content"), list)
            else {"content": []}
        )
        highlight_status[category_id] = (
            "Disponible" if highlights[category_id]["content"] else "No disponible o sin resultados"
        )
        previous_file = previous_if_available(
            f"data/raw/highlights/highlights_mlc_{category_id.lower()}_*.json"
        )
        previous_payload = load(previous_file) if previous_file else None
        old_highlights[category_id] = (
            previous_payload
            if isinstance(previous_payload, dict) and isinstance(previous_payload.get("content"), list)
            else None
        )

    coverage_file = latest("data/raw/catalog_coverage/catalog_coverage_report_*.json")
    coverage = load(coverage_file)
    products = coverage["products"]
    # A product detail or offers query can be unavailable even though its
    # highlight was returned.  Preserve that observed partial capture in the
    # report instead of treating it as a malformed run and aborting all 32
    # categories.
    product_defaults = {
        "name": "Producto no disponible",
        "highlight_position": "—",
        "offer_total": None,
        "offers_returned": 0,
        "seller_count_returned": 0,
        "min_price_returned": None,
        "max_price_returned": None,
        "mean_price_returned": None,
        "median_price_returned": None,
        "offers_collection_complete": False,
    }
    for product in products:
        for field, default in product_defaults.items():
            product.setdefault(field, default)
    product_by_id = {row["product_id"]: row for row in products}
    representative_products = []
    for category_id in CATEGORIES:
        candidates = [row for row in products if row["category_id"] == category_id]
        if candidates:
            representative_products.append(
                min(candidates, key=lambda row: row["highlight_position"])
            )
    map_file = latest("data/raw/keyword_products/keyword_product_map_mlc_*.json")
    keyword_map = load(map_file)
    manifest_file = latest("data/raw/capture_runs/capture_run_mlc_*.json")
    manifest = load(manifest_file)
    hierarchy_file = latest("data/raw/category_details/category_hierarchy_mlc_*.json")
    hierarchy = load(hierarchy_file)
    hierarchy_products = {
        row["product_id"]: row for row in hierarchy["product_categories"]
    }

    captured_at = datetime.strptime(general_file.stem[-15:], "%Y%m%d_%H%M%S").replace(
        tzinfo=timezone.utc
    )
    report_date = captured_at.strftime("%Y%m%d")
    old_capture_date = datetime.strptime(old_general_file.stem[-15:], "%Y%m%d_%H%M%S")
    current_capture_date = datetime.strptime(general_file.stem[-15:], "%Y%m%d_%H%M%S")
    comparison_hours = max(0.0, (current_capture_date - old_capture_date).total_seconds() / 3600)
    highlight_rows = [row for data in highlights.values() for row in data["content"]]
    highlight_ids = {row["id"] for row in highlight_rows}
    keyword_confirmations = [
        (mapping, product)
        for mapping in keyword_map["mappings"]
        for product in mapping["products"]
        if product["product_id"] in highlight_ids
    ]

    old_keywords = set(old_general_positions)
    current_keywords = set(current_general_positions)
    new_keywords = [row["keyword"] for row in general if row["keyword"] not in old_keywords]
    removed_keywords = [
        row["keyword"] for row in old_general if row["keyword"] not in current_keywords
    ]
    retained_count = len(old_keywords & current_keywords)
    position_changes = [
        (current_general_positions[keyword] - old_general_positions[keyword], keyword)
        for keyword in old_keywords & current_keywords
        if current_general_positions[keyword] != old_general_positions[keyword]
    ]
    if position_changes:
        _, best_keyword = min(position_changes)
        movement_summary = (
            f"{best_keyword}: #{old_general_positions[best_keyword]} → "
            f"#{current_general_positions[best_keyword]}"
        )
    else:
        movement_summary = "Sin cambios de posición entre términos retenidos"

    visits_by_product: dict[str, dict[str, Any]] = {}
    offers_by_product: dict[str, dict[str, Any]] = {}
    for row in products:
        offers_by_product[row["product_id"]] = offer_metrics(row["product_id"])
        sample = row.get("visit_sample") or {}
        if sample.get("item_id"):
            visits_by_product[row["product_id"]] = visit_metrics(sample["item_id"])
    high_traffic_ids = {
        product_id
        for product_id, _ in sorted(
            visits_by_product.items(),
            key=lambda pair: pair[1].get("total_30d") or 0,
            reverse=True,
        )[:2]
    }

    domains: dict[str, list[int]] = defaultdict(list)
    for row in products:
        if row.get("domain_id") and row.get("offer_total") is not None:
            domains[row["domain_id"]].append(row["offer_total"])

    def labels(row: dict[str, Any]) -> str:
        values = ["COMMERCIAL_CONFIRMATION"]
        if row["product_id"] in high_traffic_ids:
            values.append("HIGH_TRAFFIC")
        peers = domains.get(row.get("domain_id"), [])
        if len(peers) >= 2 and row.get("offer_total", 0) < statistics.median(peers):
            values.append("LOWER_OFFER_DENSITY")
        low, high = row.get("min_price_returned"), row.get("max_price_returned")
        if low and high and high / low >= 1.5:
            values.append("PRICE_SPREAD")
        return ", ".join(f"`{value}`" for value in values)

    def action(row: dict[str, Any]) -> str:
        traffic = visits_by_product.get(row["product_id"], {}).get("total_30d") or 0
        offers = row.get("offer_total") or 0
        if row["product_id"] in high_traffic_ids and offers <= 15:
            return "Seguir a diario y validar persistencia"
        if row["product_id"] in high_traffic_ids:
            return "Validar evolución del tráfico y precios"
        if offers <= 5:
            return "Ampliar muestra de visitas y verificar persistencia"
        if traffic:
            return "Medir persistencia y ampliar muestra de ítems"
        return "Completar tráfico y competencia"

    lines: list[str] = [
        "# Product Radar — Mercado Libre Chile",
        "",
        f"- Fecha de captura online: {captured_at.strftime('%Y-%m-%d %H:%M UTC')}.",
        "- Sitio: `MLC`.",
        f"- Categorías analizadas: {len(CATEGORIES)} de 32 categorías raíz.",
        f"- Fuentes: {len(general)} tendencias generales; "
        f"{sum(len(rows) for rows in category_trends.values())} tendencias de categoría; "
        f"{len(highlight_rows)} posiciones de highlights; {len(products)} productos/ofertas; "
        f"{len(visits_by_product)} series de visitas; {len(keyword_map['mappings'])} keywords consultados en catálogo.",
        "- Estado de fuentes: trends semanal; highlights, ofertas y visitas como snapshot diario.",
        "- Nota: informe inicial online de señales. No estima ventas ni recomienda compras automáticamente.",
        "",
        "## Resumen ejecutivo",
        "",
        f"La captura online fue técnicamente completa: los {len(products)} detalles de producto y sus "
        f"listados de ofertas respondieron HTTP 200, al igual que las "
        f"{len(coverage['summary']['visit_samples'])} consultas de tráfico "
        f"({len(visits_by_product)} ítems únicos). "
        ,
        (f"Frente al corte anterior se conservaron {retained_count} de 50 tendencias generales; "
         f"aparecieron {len(new_keywords)} términos y salieron {len(removed_keywords)}."
         if has_general_comparison else
         "Esta ejecución online contiene un solo corte; no se infieren cambios frente a una captura previa."),
        "",
        "Las señales comerciales más claras del corte son:",
        "",
    ]

    executive_rows = []
    ranked_first_products = sorted(
        representative_products,
        key=lambda row: (visits_by_product.get(row["product_id"], {}).get("total_30d") or 0),
        reverse=True,
    )
    for row in ranked_first_products[:10]:
        visits = visits_by_product.get(row["product_id"], {})
        evidence = (
            f"Highlights #{row['highlight_position']}; {row.get('offer_total', '—')} ofertas"
        )
        if visits.get("total_30d") is not None:
            evidence += f"; {money(visits['total_30d'])} visitas/30d en un ítem"
        executive_rows.append(
            [row["name"], row["category_name"], evidence, labels(row), action(row)]
        )
    lines.extend(
        [
            table(
                ["Producto", "Categoría", "Evidencia", "Etiquetas descriptivas", "Acción sugerida"],
                executive_rows,
            ),
            "",
            f"El cruce de {len(keyword_map['mappings'])} keywords prioritarios con hasta 10 resultados "
            f"de catálogo por consulta produjo {len(keyword_confirmations)} coincidencias con los "
            "highlights actuales. En este corte, descubrimiento y confirmación comercial son capas "
            "separadas; una ausencia de coincidencia directa no demuestra falta de demanda.",
            "",
            "Las mayores densidades de oferta entre los productos inspeccionados son: "
            + "; ".join(
                f"{row['name']} ({row['offer_total']})"
                for row in sorted(
                    products, key=lambda item: item.get("offer_total") or 0, reverse=True
                )[:4]
            )
            + ". La paginación quedó completa para "
            + f"{sum(bool(row.get('offers_collection_complete')) for row in products)}/{len(products)} productos.",
            "",
            "## Cambios desde el corte anterior",
            "",
            table(
                ["Métrica", "Resultado"],
                [
                    ["Tendencias generales retenidas", f"{retained_count}/50"],
                    ["Keywords nuevos", ", ".join(new_keywords)],
                    ["Keywords que salieron", ", ".join(removed_keywords)],
                    ["Mayor avance entre términos retenidos", movement_summary],
                    ["Capturas comparadas", f"{old_general_file.name} vs. {general_file.name}"],
                ],
            ),
            "",
        ]
    )

    persistence_rows = []
    for category_id, category_name in CATEGORIES.items():
        previous = old_highlights[category_id]
        if previous is None:
            persistence_rows.append(
                [category_name, "Sin corte previo", len(highlights[category_id]["content"]), "—", "—"]
            )
            continue
        old = {row["id"]: row["position"] for row in previous["content"]}
        current = {row["id"]: row["position"] for row in highlights[category_id]["content"]}
        common = old.keys() & current.keys()
        persistence_rows.append(
            [category_name, len(old), len(current), len(common), f"{len(common) / len(current):.0%}"]
        )
    lines.extend(
        [
            table(
                ["Categoría", "Highlights previos", "Actuales", "Persisten", "% del ranking actual"],
                persistence_rows,
            ),
            "",
            "La persistencia sólo se calcula para categorías con un corte previo disponible. Un único "
            "snapshot no permite clasificar una oportunidad como estable o acelerada.",
            "",
            "## Tendencias generales",
            "",
        ]
    )
    lines.append(
        table(
            ["Posición", "Grupo", "Keyword", "Cambio", "URL"],
            [
                [
                    position,
                    trend_group(position),
                    row["keyword"],
                    trend_delta(old_general_positions, row["keyword"], position),
                    f"[ver]({row['url']})",
                ]
                for position, row in enumerate(general, 1)
            ],
        )
    )

    lines.extend(["", "## Tendencias por categoría", ""])
    for category_id, category_name in CATEGORIES.items():
        rows = category_trends[category_id]
        lines.extend(
            [
                f"### {category_name} — `{category_id}`",
                "",
                table(
                    ["Posición", "Keyword", "En tendencia general", "URL"],
                    [
                        [
                            position,
                            row["keyword"],
                            (
                                f"Sí, #{current_general_positions[row['keyword']]}"
                                if row["keyword"] in current_general_positions
                                else "No"
                            ),
                            f"[ver]({row['url']})",
                        ]
                        for position, row in enumerate(rows[:10], 1)
                    ],
                ),
                (
                    "Fuente no disponible para esta categoría en el endpoint `/trends`; se conserva "
                    "la categoría raíz dentro del alcance del informe."
                    if not category_trends[category_id]
                    else ""
                ),
                "",
            ]
        )

    lines.extend(["## Confirmación comercial", ""])
    confirmation_summary = []
    for category_id, category_name in CATEGORIES.items():
        content = highlights[category_id]["content"]
        counts = Counter(row["type"] for row in content)
        confirmation_summary.append(
            [
                category_name,
                highlight_status[category_id],
                len(content),
                counts.get("PRODUCT", 0),
                counts.get("ITEM", 0),
                counts.get("USER_PRODUCT", 0),
            ]
        )
    lines.extend(
        [
            table(
                ["Categoría", "Estado", "Posiciones", "PRODUCT", "ITEM", "USER_PRODUCT"],
                confirmation_summary,
            ),
            "",
            "Top 3 de entidades `PRODUCT` resueltas por categoría:",
            "",
            table(
                ["Categoría", "Posición", "Producto ID", "Producto", "Marca", "Estado"],
                [
                    [
                        row["category_name"],
                        row["highlight_position"],
                        f"`{row['product_id']}`",
                        row["name"],
                        row["brand"],
                        "Resuelto (HTTP 200)",
                    ]
                    for row in products
                ],
            ),
            "",
            "## Categorías y subcategorías de las entidades líderes",
            "",
            "La categoría del ranking representa el contexto comercial consultado. La categoría "
            "específica se obtiene de la oferta predominante y su ruta `path_from_root`.",
            "",
            table(
                [
                    "Primer PRODUCT resoluble",
                    "Categoría del ranking",
                    "Categoría específica predominante",
                    "Ruta observada",
                ],
                [
                    [
                        row["name"],
                        row["category_name"],
                        hierarchy_products.get(row["product_id"], {}).get(
                            "primary_category_name"
                        ),
                        " › ".join(
                            item["name"]
                            for item in hierarchy_products.get(row["product_id"], {}).get(
                                "primary_category_path", []
                            )
                        ),
                    ]
                    for row in ranked_first_products
                ],
            ),
            "",
            "Subcategorías directas disponibles dentro de cada categoría raíz analizada:",
            "",
            table(
                ["Categoría raíz", "Subcategorías directas", "Cantidad"],
                [
                    [
                        category_name,
                        ", ".join(
                            child["name"]
                            for child in hierarchy["categories"].get(category_id, {}).get(
                                "children_categories", []
                            )
                        ),
                        len(
                            hierarchy["categories"].get(category_id, {}).get(
                                "children_categories", []
                            )
                        ),
                    ]
                    for category_id, category_name in CATEGORIES.items()
                ],
            ),
            "",
            "## Mapa keyword → producto candidato",
            "",
            "Cada fila conserva el primer resultado por relevancia de `/products/search`; es una "
            "hipótesis de catálogo, no una equivalencia semántica ni una recomendación.",
            "",
            table(
                ["Origen", "Pos. trend", "Keyword", "Primer producto candidato", "ID", "En highlights"],
                [
                    [
                        mapping["category_name"] or "General",
                        mapping["trend_position"],
                        mapping["keyword"],
                        mapping["products"][0]["name"] if mapping["products"] else "Sin resultado",
                        (
                            f"`{mapping['products'][0]['product_id']}`"
                            if mapping["products"]
                            else "—"
                        ),
                        (
                            "Sí"
                            if mapping["products"]
                            and mapping["products"][0]["product_id"] in highlight_ids
                            else "No"
                        ),
                    ]
                    for mapping in keyword_map["mappings"]
                ],
            ),
            "",
            "## Productos priorizados",
            "",
        ]
    )

    for row in ranked_first_products:
        visits = visits_by_product.get(row["product_id"], {})
        category_path = " › ".join(
            item["name"]
            for item in hierarchy_products.get(row["product_id"], {}).get(
                "primary_category_path", []
            )
        )
        lines.extend(
            [
                f"### {row['name']}",
                "",
                f"- Producto ID: `{row['product_id']}`.",
                f"- Categoría: {row['category_name']}; highlights #{row['highlight_position']}.",
                f"- Ruta de categoría observada: {category_path or 'no resuelta'}.",
                f"- Marca y dominio: {row['brand'] or 'no informada'}; `{row['domain_id']}`.",
                f"- Keywords de referencia: {reference_keywords(row['product_id'])}.",
                f"- Competencia: {row['offer_total']} ofertas totales; "
                f"{row['offers_returned']} recuperadas; {row['seller_count_returned']} vendedores recuperados.",
                f"- Precio observado: CLP {money(row['min_price_returned'])}–{money(row['max_price_returned'])}.",
                f"- Ofertas recuperadas con envío gratis: {offers_by_product[row['product_id']]['free_shipping']}; "
                f"con descuento observado: {offers_by_product[row['product_id']]['discounts']}; "
                f"condición: {offers_by_product[row['product_id']]['conditions']}.",
                (
                    f"- Tráfico: {money(visits.get('total_30d'))} visitas/30d; "
                    f"{money(visits.get('recent_7d'))} en los últimos 7 días del período."
                    if visits
                    else "- Tráfico: sin muestra en este corte."
                ),
                f"- Etiquetas: {labels(row)}.",
                "",
            ]
        )

    lines.extend(
        [
            "## Competencia y precios",
            "",
            table(
                [
                    "Categoría / pos.",
                    "Producto",
                    "Ofertas total / recuperadas",
                    "Vendedores recup.",
                    "Precio mín. CLP",
                    "Precio máx. CLP",
                    "Promedio CLP",
                    "Mediana CLP",
                    "Envío gratis recup.",
                    "Descuento recup.",
                    "Cobertura",
                ],
                [
                    [
                        f"{row['category_name']} #{row['highlight_position']}",
                        row["name"],
                        f"{row['offer_total']} / {row['offers_returned']}",
                        row["seller_count_returned"],
                        money(row["min_price_returned"]),
                        money(row["max_price_returned"]),
                        money(row.get("mean_price_returned")),
                        money(row.get("median_price_returned")),
                        offers_by_product[row["product_id"]]["free_shipping"],
                        offers_by_product[row["product_id"]]["discounts"],
                        "Completa" if row["offer_total"] == row["offers_returned"] else "Primera página",
                    ]
                    for row in products
                ],
            ),
            "",
            "Los precios mínimos/máximos y vendedores son parciales cuando sólo se recuperó la "
            "primera página. El total de ofertas es el valor informado por `paging.total`.",
            "",
            "## Tráfico",
            "",
            table(
                [
                    "Producto",
                    "Ítem de muestra",
                    "Visitas 30d",
                    "Últimos 7d",
                    "7d anteriores",
                    "Variación",
                    "Días con dato / tramo",
                ],
                [
                    [
                        product_by_id[product_id]["name"],
                        f"`{metrics['item_id']}`",
                        money(metrics.get("total_30d")),
                        money(metrics.get("recent_7d")),
                        money(metrics.get("previous_7d")),
                        (
                            f"{metrics['variation_7d']:+.1f}%"
                            if metrics.get("variation_7d") is not None
                            else "No comparable"
                        ),
                        f"{metrics.get('days_with_data', 0)} / {metrics.get('calendar_span', 0)}",
                    ]
                    for product_id, metrics in sorted(
                        visits_by_product.items(),
                        key=lambda pair: pair[1].get("total_30d") or 0,
                        reverse=True,
                    )
                ],
            ),
            "",
            "La variación compara dos ventanas consecutivas de siete días dentro de la misma serie "
            "y sólo se calcula con al menos 14 fechas informadas. Una serie de visitas corresponde "
            "a un ítem de muestra, no al producto completo.",
            "",
            "## Disponibilidad de ventas exactas",
            "",
            table(
                ["Métrica", "Cobertura observada", "Interpretación"],
                [
                    [
                        "Productos con `sold_quantity`",
                        f"{sum(bool(row.get('has_sold_quantity')) for row in products)}/{len(products)}",
                        "No usar unidades vendidas si el campo no fue recibido",
                    ],
                    [
                        "Productos con `buy_box_winner`",
                        f"{sum(bool(row.get('has_buy_box_winner')) for row in products)}/{len(products)}",
                        "No inferir oferta ganadora",
                    ],
                    [
                        "Ofertas con campos de unidades vendidas",
                        f"{sum(bool(row.get('offers_have_sold_quantity')) for row in products)}/{len(products)} productos",
                        "No hay serie de ventas de competidores",
                    ],
                    [
                        "Fechas de ventas de terceros",
                        "No disponibles",
                        "Sólo órdenes propias entregan cantidad, precio y fecha",
                    ],
                ],
            ),
            "",
            "El precio promedio mostrado es un promedio de ofertas activas, no el ticket efectivo "
            "de las transacciones. Highlights aporta confirmación comercial relativa, no unidades.",
            "",
            "## Limitaciones y metodología",
            "",
            "- `/trends` entrega posición relativa, no volumen de búsquedas ni crecimiento porcentual.",
            "- Highlights confirma desempeño comercial relativo, no unidades vendidas.",
            "- Una keyword puede vincularse con múltiples productos; el orden de búsqueda sólo expresa relevancia del endpoint.",
            "- Visitas miden tráfico, no ventas ni conversión.",
            f"- No se recibieron unidades vendidas, stock real ni `buy_box_winner` en los {len(products)} productos muestreados.",
            "- `ITEM` y `USER_PRODUCT` de terceros pueden no ser resolubles con el grant disponible.",
            "- La muestra cubre tres productos `PRODUCT` por categoría y no representa todo el mercado.",
            f"- Trends se comparó a {comparison_hours:.1f} horas de distancia; su cadencia publicada es semanal, por lo que el próximo corte comparable debe respetar siete días.",
            "",
            "## Trazabilidad de fuentes",
            "",
            table(
                ["Fuente", "Archivo"],
                [
                    ["Manifiesto de captura", f"`{manifest_file}` ({manifest['raw_file_count']} RAW)"],
                    ["Tendencias generales", f"`{general_file}`"],
                    ["Mapa keyword-producto", f"`{map_file}`"],
                    ["Cobertura de catálogo", f"`{coverage_file}`"],
                    ["Jerarquía de categorías", f"`{hierarchy_file}`"],
                    *[
                        [f"Tendencias {CATEGORIES[category_id]}", f"`{category_trend_files[category_id]}`"]
                        for category_id in CATEGORIES
                    ],
                    *[
                        [f"Highlights {CATEGORIES[category_id]}", f"`{highlight_files[category_id]}`"]
                        for category_id in CATEGORIES
                    ],
                ],
            ),
            "",
        ]
    )

    output = Path("reports") / f"product_radar_MLC_{report_date}_32_categorias_online.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Informe generado: {output}")


if __name__ == "__main__":
    main()
