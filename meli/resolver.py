from typing import Any

from .client import MercadoLibreClient


ENTITY_ENDPOINTS = {
    "PRODUCT": "/products/{entity_id}",
    "ITEM": "/items/{entity_id}",
    "USER_PRODUCT": "/user-products/{entity_id}",
}


def endpoint_for(entity_type: str, entity_id: str) -> str:
    normalized_type = entity_type.strip().upper()
    try:
        template = ENTITY_ENDPOINTS[normalized_type]
    except KeyError as exc:
        supported = ", ".join(ENTITY_ENDPOINTS)
        raise ValueError(
            f"Tipo no soportado: {entity_type}. Tipos válidos: {supported}"
        ) from exc
    return template.format(entity_id=entity_id.strip())


def resolve_entity(
    client: MercadoLibreClient,
    entity_type: str,
    entity_id: str,
) -> Any:
    return client.get(endpoint_for(entity_type, entity_id))
