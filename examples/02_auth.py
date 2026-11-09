import json

from dotenv import load_dotenv

from meli.client import MercadoLibreClient


def main() -> None:
    load_dotenv()
    client = MercadoLibreClient()
    user = client.get("/users/me")
    print(
        json.dumps(
            {
                "id": user.get("id"),
                "nickname": user.get("nickname"),
                "site_id": user.get("site_id"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
