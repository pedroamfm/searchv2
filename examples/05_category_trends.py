import argparse

from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.report_config import REPORT_CATEGORIES
from meli.storage import save_json


DEFAULT_CATEGORIES = REPORT_CATEGORIES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta tendencias para categorías de Mercado Libre."
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
        endpoint = f"/trends/{client.site_id}/{category_id}"
        response = client.get_response(endpoint)
        try:
            trends = response.json()
        except ValueError:
            trends = {"text": response.text[:2000]}

        filename = save_json(
            trends,
            "data/raw/trends/categories",
            f"trends_{client.site_id.lower()}_{category_id.lower()}",
        )
        name = DEFAULT_CATEGORIES.get(category_id, "Categoría personalizada")
        if response.ok and isinstance(trends, list):
            preview = ", ".join(
                trend.get("keyword", "<sin keyword>") for trend in trends[:3]
            )
            print(f"{category_id} — {name}: {len(trends)} tendencias")
            print(f"  Primeras 3: {preview}")
        else:
            print(f"{category_id} — {name}: tendencias no disponibles (HTTP {response.status_code})")
        print(f"  RAW: {filename}")


if __name__ == "__main__":
    main()
