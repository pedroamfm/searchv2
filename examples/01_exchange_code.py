import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from meli.oauth import exchange_code, persist_tokens


SESSION_FILE = Path(".oauth_session.json")


def callback_parameters(callback_url: str) -> tuple[str, str]:
    query = parse_qs(urlparse(callback_url.strip()).query)
    if query.get("error"):
        raise RuntimeError(f"Mercado Libre devolvió: {query['error'][0]}")
    if not query.get("code") or not query.get("state"):
        raise ValueError("La URL debe contener los parámetros code y state")
    return query["code"][0], query["state"][0]


def main() -> None:
    load_dotenv()
    if not SESSION_FILE.exists():
        raise RuntimeError("Ejecuta primero examples/00_authorize.py")

    session = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    callback_url = input("Pega la URL completa de redirección: ")
    code, returned_state = callback_parameters(callback_url)

    if returned_state != session["state"]:
        raise RuntimeError("El state recibido no coincide con la sesión OAuth")

    token = exchange_code(code, session.get("code_verifier"))
    print("\nToken obtenido correctamente.")
    print(f"user_id: {token.get('user_id')}")
    print(f"scope: {token.get('scope')}")
    print(f"expires_in: {token.get('expires_in')}")
    persist_tokens(token)
    print("\nTokens guardados en .env; sus valores no se muestran.")


if __name__ == "__main__":
    main()
