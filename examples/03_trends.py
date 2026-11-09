from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.storage import save_json


def main() -> None:
    load_dotenv()
    client = MercadoLibreClient()
    endpoint = f"/trends/{client.site_id}"
    response = client.get_response(endpoint)
    try:
        payload = response.json()
    except ValueError:
        payload = {"text": response.text[:2000]}

    # Mercado Libre can temporarily withdraw the site-wide trends resource
    # (currently it returns HTTP 404 for MLC).  It must not invalidate the
    # complete 32-category report: category trends, highlights, catalogue and
    # visits are independently collected.  Keep the HTTP evidence separately
    # and save an empty, schema-compatible trend list for the report builder.
    trends = payload if response.ok and isinstance(payload, list) else []
    if not response.ok:
        save_json(
            {
                "endpoint": endpoint,
                "http_status": response.status_code,
                "payload": payload,
            },
            "data/raw/trends/errors",
            f"trends_{client.site_id.lower()}_unavailable",
        )

    filename = save_json(
        trends,
        "data/raw/trends",
        f"trends_{client.site_id.lower()}",
    )

    if not response.ok:
        print(
            f"Tendencias generales no disponibles (HTTP {response.status_code}) "
            f"en {endpoint}; se continuará con tendencias por categoría."
        )
    print(f"Tendencias recibidas: {len(trends)}")
    for position, trend in enumerate(trends[:10], start=1):
        print(f"{position:>2}. {trend.get('keyword', '<sin keyword>')}")
    print(f"RAW guardado en: {filename}")


if __name__ == "__main__":
    main()
