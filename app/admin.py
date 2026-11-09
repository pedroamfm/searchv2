"""Create or rotate the local Product Radar administrator."""

from __future__ import annotations

import argparse
import getpass

from app.auth import create_admin
from app.config import get_settings
from app.database import database_connection
from app.migrations import is_current


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear o rotar administrador local.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Repetir contraseña: ")
    if len(password) < 12 or password != confirmation:
        raise SystemExit("Las contraseñas no coinciden o son demasiado cortas.")
    settings = get_settings()
    if not is_current(settings.database_path):
        raise SystemExit("La base requiere migración: python -m app.migrations upgrade")
    with database_connection(settings.database_path, read_only=False) as connection:
        create_admin(connection, args.email, args.name, password)
    print("Administrador creado o rotado. La contraseña no se mostró ni se guardó fuera de SQLite.")


if __name__ == "__main__":
    main()
