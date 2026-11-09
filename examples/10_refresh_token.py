from dotenv import load_dotenv

from meli.oauth import persist_tokens, refresh_access_token


def main() -> None:
    load_dotenv()
    tokens = refresh_access_token()
    persist_tokens(tokens)
    print("Tokens OAuth renovados y guardados en .env (valores ocultos).")
    if tokens.get("expires_in") is not None:
        print(f"Expiración informada: {tokens['expires_in']} segundos")
    if tokens.get("user_id") is not None:
        print(f"Usuario autorizado: {tokens['user_id']}")


if __name__ == "__main__":
    main()
