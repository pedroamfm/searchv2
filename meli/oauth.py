import base64
import hashlib
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import requests


AUTHORIZATION_URL = "https://auth.mercadolibre.cl/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Falta {name}")
    return value


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AuthorizationRequest:
    url: str
    state: str
    code_verifier: str | None = None


def build_authorization_request(use_pkce: bool = False) -> AuthorizationRequest:
    client_id = _required_env("MELI_CLIENT_ID")
    redirect_uri = _required_env("MELI_REDIRECT_URI")
    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    code_verifier = None

    if use_pkce:
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        params["code_challenge"] = (
            base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        )
        params["code_challenge_method"] = "S256"

    return AuthorizationRequest(
        url=f"{AUTHORIZATION_URL}?{urlencode(params)}",
        state=state,
        code_verifier=code_verifier,
    )


def exchange_code(code: str, code_verifier: str | None = None) -> dict:
    form = {
        "grant_type": "authorization_code",
        "client_id": _required_env("MELI_CLIENT_ID"),
        "client_secret": _required_env("MELI_CLIENT_SECRET"),
        "code": code,
        "redirect_uri": _required_env("MELI_REDIRECT_URI"),
    }
    if code_verifier:
        form["code_verifier"] = code_verifier

    response = requests.post(
        TOKEN_URL,
        data=form,
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str | None = None) -> dict:
    """Exchange the current refresh token for a rotated OAuth token pair."""
    form = {
        "grant_type": "refresh_token",
        "client_id": _required_env("MELI_CLIENT_ID"),
        "client_secret": _required_env("MELI_CLIENT_SECRET"),
        "refresh_token": refresh_token or _required_env("MELI_REFRESH_TOKEN"),
    }
    response = requests.post(
        TOKEN_URL,
        data=form,
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def persist_tokens(tokens: dict, env_file: str | Path = ".env") -> None:
    """Atomically replace OAuth tokens in an existing dotenv file."""
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token or not refresh_token:
        raise ValueError("La respuesta OAuth no contiene ambos tokens")

    path = Path(env_file)
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    replacements = {
        "MELI_ACCESS_TOKEN": access_token,
        "MELI_REFRESH_TOKEN": refresh_token,
    }
    found: set[str] = set()
    output: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in replacements:
            newline = "\n" if line.endswith("\n") else ""
            output.append(f"{key}={replacements[key]}{newline}")
            found.add(key)
        else:
            output.append(line)

    missing = replacements.keys() - found
    if missing:
        if output and not output[-1].endswith("\n"):
            output[-1] += "\n"
        output.extend(f"{key}={replacements[key]}\n" for key in sorted(missing))

    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.writelines(output)
    temporary.chmod(mode)
    temporary.replace(path)
