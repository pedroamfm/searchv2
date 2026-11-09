from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.storage import save_json


def main() -> None:
    load_dotenv()
    client = MercadoLibreClient()
    endpoint = f"/sites/{client.site_id}/categories"
    categories = client.get(endpoint)

    if not isinstance(categories, list):
        raise TypeError(
            f"Se esperaba una lista en {endpoint}; se recibió "
            f"{type(categories).__name__}"
        )

    filename = save_json(
        categories,
        "data/raw/categories",
        f"categories_{client.site_id.lower()}",
    )

    print(f"Categorías raíz recibidas: {len(categories)}")
    for category in categories:
        print(f"{category.get('id', '<sin id>')}: {category.get('name', '<sin nombre>')}")
    print(f"RAW guardado en: {filename}")


if __name__ == "__main__":
    main()
