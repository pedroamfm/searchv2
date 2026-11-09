# Persistencia SQLite — Product Radar

La base local se crea en `data/product_radar.sqlite3`. Los JSON de
`data/raw/` siguen siendo la fuente de evidencia; SQLite contiene datos
normalizados para análisis temporal y generación de informes.

## Comandos

```bash
.venv/bin/python -m examples.15_init_database
.venv/bin/python -m examples.16_ingest_raw_to_sqlite
```

La importación es idempotente: puede ejecutarse después de cada captura sin
duplicar snapshots ya almacenados.

## Tablas principales

| Tabla | Contenido |
|---|---|
| `capture_runs` | Corridas y manifiestos RAW |
| `raw_sources` | Archivo, endpoint, hash y timestamp |
| `trend_snapshots` | Keywords y posición por fecha/categoría |
| `highlight_snapshots` | Ranking comercial relativo |
| `product_snapshots` | Producto, marca, dominio y contexto del ranking |
| `offer_snapshots` | Ofertas, precio, vendedor, envío y categoría |
| `visit_snapshots` | Serie diaria de visitas por ítem |
| `keyword_product_mappings` | Hipótesis keyword → producto |
| `category_snapshots` | Categorías y jerarquía |
| `product_category_snapshots` | Categoría específica predominante por producto |

Todas las tablas de señales incluyen `source_id`, por lo que el modelo admite
futuras fuentes además de Mercado Libre. Cada snapshot conserva
`raw_source_id` para volver al JSON de origen.

## Límites de interpretación

SQLite no crea datos que la API no entrega: `sold_quantity` y fechas exactas
de ventas de competidores permanecen ausentes cuando Mercado Libre no los
devuelve. Los precios almacenados son precios de ofertas observadas y las
visitas son tráfico, no ventas.
