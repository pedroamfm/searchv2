"""Curated, auditable keyword portfolio for the supply-and-taxonomy capture."""

from typing import TypedDict


class PriorityKeyword(TypedDict):
    keyword: str
    portfolio: str


PRIORITY_KEYWORDS: tuple[PriorityKeyword, ...] = (
    {"keyword": "auriculares inalambricos bluetooth", "portfolio": "Tecnología y Accesorios"},
    {"keyword": "smartwatch deportivo sumergible", "portfolio": "Tecnología y Accesorios"},
    {"keyword": "soporte celular auto magnetico", "portfolio": "Tecnología y Accesorios"},
    {"keyword": "cargador carga rapida usb c", "portfolio": "Tecnología y Accesorios"},
    {"keyword": "freidora de aire digital", "portfolio": "Hogar, Confort y Organización"},
    {"keyword": "lampara solar sensor movimiento", "portfolio": "Hogar, Confort y Organización"},
    {"keyword": "organizador cajones ropa acrilico", "portfolio": "Hogar, Confort y Organización"},
    {"keyword": "cortinas blackout termica", "portfolio": "Hogar, Confort y Organización"},
    {"keyword": "serum vitamina c acido hialuronico", "portfolio": "Belleza, Salud y Cuidado Personal"},
    {"keyword": "cepillo secador alisador pelo", "portfolio": "Belleza, Salud y Cuidado Personal"},
    {"keyword": "corrector postura espalda ajustable", "portfolio": "Belleza, Salud y Cuidado Personal"},
    {"keyword": "maquina cortar pelo profesional", "portfolio": "Belleza, Salud y Cuidado Personal"},
    {"keyword": "botella termica acero inoxidable 1l", "portfolio": "Fitness, Aire Libre y Movilidad"},
    {"keyword": "bandas elasticas musculacion set", "portfolio": "Fitness, Aire Libre y Movilidad"},
    {"keyword": "mochila antirrobo impermeable notebook", "portfolio": "Fitness, Aire Libre y Movilidad"},
    {"keyword": "camara seguridad wifi exterior 360", "portfolio": "Herramientas, Auto y Mascotas"},
    {"keyword": "taladro percutor inalambrico bateria", "portfolio": "Herramientas, Auto y Mascotas"},
    {"keyword": "aspiradora portatil auto inalambrica", "portfolio": "Herramientas, Auto y Mascotas"},
    {"keyword": "cama perro antiestres lavable", "portfolio": "Herramientas, Auto y Mascotas"},
    {"keyword": "tira led rgb inteligente wifi", "portfolio": "Herramientas, Auto y Mascotas"},
)
