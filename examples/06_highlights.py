import argparse
from collections import Counter

from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.report_config import REPORT_CATEGORIES
from meli.storage import save_json


DEFAULT_CATEGORIES = REPORT_CATEGORIES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta los productos más vendidos por categoría."
    )
    parser.add_argument(
        "category_ids",
        nargs="*",
        help="IDs de categoría; si se omiten se usa la muestra inicial.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    client = MercadoLibreClient()
    category_ids = args.category_ids or list(DEFAULT_CATEGORIES)

    for category_id in category_ids:
        endpoint = f"/highlights/{client.site_id}/category/{category_id}"
        http_response = client.get_response(endpoint)
        try:
            response = http_response.json()
        except ValueError:
            response = {"text": http_response.text[:2000]}
        content = response.get("content", []) if isinstance(response, dict) else []

        filename = save_json(
            response,
            "data/raw/highlights",
            f"highlights_{client.site_id.lower()}_{category_id.lower()}",
        )
        name = DEFAULT_CATEGORIES.get(category_id, "Categoría personalizada")
        type_counts = Counter(entry.get("type", "UNKNOWN") for entry in content)

        if not http_response.ok:
            print(f"{category_id} — {name}: highlights no disponibles (HTTP {http_response.status_code})")
            print(f"  RAW: {filename}")
            continue
        print(f"{category_id} — {name}: {len(content)} resultados")
        print(f"  Tipos: {dict(type_counts)}")
        for entry in content[:5]:
            print(
                f"  {entry.get('position', '?'):>2}. "
                f"{entry.get('id', '<sin id>')} "
                f"[{entry.get('type', 'UNKNOWN')}]"
            )
        print(f"  RAW: {filename}")


if __name__ == "__main__":
    main()
