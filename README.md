# Product Radar

Product Radar recopila y organiza información pública de Mercado Libre para observar tendencias de búsqueda, categorías, productos destacados y ofertas. El sistema conserva capturas locales para comparar cambios y generar informes.

## Características

- Autorización OAuth de Mercado Libre y cliente API con límites de solicitudes.
- Captura de tendencias, categorías, productos destacados, ofertas y métricas disponibles.
- Almacenamiento de respuestas originales y datos normalizados en SQLite.
- Historial de capturas con trazabilidad hacia la evidencia de origen.
- Informes Markdown y exploración de productos, tendencias, operaciones y evidencia mediante una aplicación web.
- API FastAPI, worker de tareas y frontend Next.js, ejecutables con Docker Compose.
- Cuentas locales con sesiones, control CSRF y acceso por roles.

Las métricas reflejan los datos que la API entrega; no representan ventas verificadas ni datos que Mercado Libre no expone.

## Requisitos

- Python 3.13.
- Docker Compose para ejecutar la aplicación web completa.
- Una aplicación OAuth de Mercado Libre con acceso permitido a los endpoints que se quieran consultar.

## Desarrollo local

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Completa las variables `MELI_CLIENT_ID`, `MELI_CLIENT_SECRET` y `MELI_REDIRECT_URI` en `.env`, realiza la autorización OAuth y guarda allí los tokens. El archivo `.env` contiene credenciales: mantenlo fuera de Git y no compartas su contenido. Los ejemplos de configuración publicados contienen valores vacíos.

Consulta inicial de tendencias:

```bash
.venv/bin/python -m examples.00_authorize
.venv/bin/python -m examples.01_exchange_code
.venv/bin/python -m examples.02_auth
.venv/bin/python -m examples.03_trends
```

El código de autorización es de un solo uso. El ejemplo de intercambio guarda los tokens directamente en el archivo `.env` local y no los imprime en pantalla.

## Aplicación web

Después de configurar `.env`:

```bash
docker compose up -d --build
```

La interfaz se sirve en `http://localhost:3000`. La API y el worker permanecen dentro de la red de Compose. Para aplicar migraciones de SQLite:

```bash
.venv/bin/python -m app.migrations current
.venv/bin/python -m app.migrations upgrade
```

La aplicación también permite generar informes Markdown y cargar capturas en SQLite para análisis histórico. Revisa [DATABASE.md](DATABASE.md) para conocer las entidades y la trazabilidad.

## Datos y credenciales

Las capturas JSON, la base SQLite, los informes, las copias de seguridad, `.env`, sesiones OAuth y entornos virtuales son artefactos locales y no forman parte del código fuente publicado. Usa `.env.example` como referencia y nunca reemplaces sus valores vacíos con credenciales antes de hacer un commit.

## Pruebas

```bash
.venv/bin/pytest
```

El frontend tiene sus propios comandos definidos en `frontend/package.json`.
