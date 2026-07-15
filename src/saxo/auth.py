"""Saxo OpenAPI OAuth Authorization Code Grant flow (RFC 6749 section 4.1).

Run as a script to perform the interactive login against SAXO_ENVIRONMENT:
    python -m src.saxo.auth
"""

import json
import secrets
import time
import urllib.parse
import webbrowser
from typing import Optional

import requests

from src.common.callback_server import listen_for_callback
from src.config import DATA_DIR, SaxoConfig, load_saxo_config

def _token_file(config: SaxoConfig):
    return DATA_DIR / f"saxo_tokens_{config.environment.lower()}.json"


def _build_authorize_url(config: SaxoConfig, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": config.app_key,
        "redirect_uri": config.redirect_uri,
        "state": state,
    }
    return f"{config.auth_base_url}/authorize?{urllib.parse.urlencode(params)}"


def _exchange_code_for_tokens(config: SaxoConfig, code: str) -> dict:
    response = requests.post(
        f"{config.auth_base_url}/token",
        auth=(config.app_key, config.app_secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _refresh_tokens(config: SaxoConfig, refresh_token: str) -> dict:
    response = requests.post(
        f"{config.auth_base_url}/token",
        auth=(config.app_key, config.app_secret),
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _save_tokens(config: SaxoConfig, token_data: dict) -> None:
    now = time.time()
    record = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "access_token_expires_at": now + int(token_data["expires_in"]),
        "refresh_token_expires_at": now + int(token_data["refresh_token_expires_in"]),
    }
    _token_file(config).write_text(json.dumps(record, indent=2))


def _load_tokens(config: SaxoConfig) -> Optional[dict]:
    token_file = _token_file(config)
    if not token_file.is_file():
        return None
    return json.loads(token_file.read_text())


def login(config: Optional[SaxoConfig] = None) -> str:
    """Runs the interactive Authorization Code Grant flow and stores the tokens.

    Opens the system browser, blocks until Saxo redirects back to the local
    callback listener, then exchanges the code for tokens. Returns the access
    token.
    """
    config = config or load_saxo_config()
    port = urllib.parse.urlparse(config.redirect_uri).port
    state = secrets.token_urlsafe(24)

    auth_url = _build_authorize_url(config, state)
    print(f"Opening browser for Saxo login ({config.environment})...")
    print(f"If it doesn't open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    params = listen_for_callback(port)

    if "error" in params:
        raise RuntimeError(f"Saxo authorization failed: {params}")
    if params.get("state", [None])[0] != state:
        raise RuntimeError("State mismatch on OAuth callback - possible CSRF, aborting.")
    code = params.get("code", [None])[0]
    if not code:
        raise RuntimeError(f"No authorization code in callback: {params}")

    token_data = _exchange_code_for_tokens(config, code)
    _save_tokens(config, token_data)
    print("Saxo login successful, tokens saved to", _token_file(config))
    return token_data["access_token"]


def get_valid_access_token(config: Optional[SaxoConfig] = None) -> str:
    """Returns a valid access token, refreshing or re-authenticating as needed."""
    config = config or load_saxo_config()
    tokens = _load_tokens(config)

    if tokens is None:
        return login(config)

    now = time.time()
    if now < tokens["access_token_expires_at"] - 30:
        return tokens["access_token"]

    if now < tokens["refresh_token_expires_at"] - 30:
        token_data = _refresh_tokens(config, tokens["refresh_token"])
        _save_tokens(config, token_data)
        return token_data["access_token"]

    return login(config)


if __name__ == "__main__":
    get_valid_access_token()
