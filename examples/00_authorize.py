import json
import os
from pathlib import Path

from dotenv import load_dotenv

from meli.oauth import build_authorization_request, env_flag


SESSION_FILE = Path(".oauth_session.json")


def main() -> None:
    load_dotenv()
    request = build_authorization_request(
        use_pkce=env_flag("MELI_USE_PKCE")
    )

    SESSION_FILE.write_text(
        json.dumps(
            {
                "state": request.state,
                "code_verifier": request.code_verifier,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.chmod(SESSION_FILE, 0o600)

    print("Abre esta URL en el navegador y autoriza la aplicación:\n")
    print(request.url)
    print(f"\nSesión OAuth guardada localmente en {SESSION_FILE}")


if __name__ == "__main__":
    main()
