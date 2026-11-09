import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

from meli.client import MercadoLibreClient
from meli.resolver import ENTITY_ENDPOINTS, resolve_entity
from meli.storage import save_json


SAMPLE_ENTITIES = [
    ("PRODUCT", "MLC75478520"),
    ("ITEM", "MLC2771781042"),
    ("USER_PRODUCT", "MLCU3515284776"),
]


def entity_argument(value: str) -> tuple[str, str]:
    try:
        entity_type, entity_id = value.split(":", maxsplit=1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Usa el formato TIPO:ID") from exc

    entity_type = entity_type.strip().upper()
    entity_id = entity_id.strip()
    if entity_type not in ENTITY_ENDPOINTS:
        raise argparse.ArgumentTypeError(f"Tipo no soportado: {entity_type}")
    if not entity_id:
        raise argparse.ArgumentTypeError("El ID no puede estar vacío")
    return entity_type, entity_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resuelve IDs PRODUCT, ITEM y USER_PRODUCT."
    )
    parser.add_argument(
        "entities",
        nargs="*",
        type=entity_argument,
        help="Entidades en formato TIPO:ID; si se omiten usa la muestra capturada.",
    )
    return parser.parse_args()


def response_error(exc: requests.HTTPError) -> dict:
    response = exc.response
    if response is None:
        return {"error": "http_error", "message": str(exc)}
    try:
        body = response.json()
    except ValueError:
        body = response.text
    return {
        "error": "http_error",
        "status_code": response.status_code,
        "body": body,
    }


def print_summary(entity_type: str, data: dict) -> None:
    if entity_type == "PRODUCT":
        print(f"  name: {data.get('name')}")
        print(f"  status: {data.get('status')}")
        print(f"  domain_id: {data.get('domain_id')}")
        winner = data.get("buy_box_winner") or {}
        print(f"  buy_box_item: {winner.get('item_id')}")
    elif entity_type == "ITEM":
        print(f"  title: {data.get('title')}")
        print(f"  category_id: {data.get('category_id')}")
        print(f"  price: {data.get('price')} {data.get('currency_id', '')}")
        print(f"  sold_quantity: {data.get('sold_quantity')}")
    else:
        print(f"  family_name: {data.get('family_name')}")
        print(f"  family_id: {data.get('family_id')}")
        print(f"  user_id: {data.get('user_id')}")


def main() -> None:
    load_dotenv()
    args = parse_args()
    client = MercadoLibreClient()
    entities = args.entities or SAMPLE_ENTITIES

    for entity_type, entity_id in entities:
        directory = Path("data/raw/entities") / entity_type.lower()
        prefix = f"{entity_type.lower()}_{entity_id.lower()}"
        print(f"Resolviendo {entity_type} {entity_id}")
        try:
            data = resolve_entity(client, entity_type, entity_id)
        except requests.HTTPError as exc:
            error = response_error(exc)
            filename = save_json(error, directory / "errors", prefix)
            print(f"  HTTP {error.get('status_code', '?')}: respuesta guardada en {filename}")
            continue

        filename = save_json(data, directory, prefix)
        if isinstance(data, dict):
            print_summary(entity_type, data)
        print(f"  RAW: {filename}")


if __name__ == "__main__":
    main()
