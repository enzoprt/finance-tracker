"""Enable Banking account-linking (PSD2 consent, Account Information Service).

Run as a script to link a bank account:
    python -m src.enablebanking.auth LCL
    python -m src.enablebanking.auth N26
"""

import json
import secrets
import sys
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.common.callback_server import listen_for_callback
from src.config import DATA_DIR, EnableBankingConfig, load_enable_banking_config
from src.enablebanking.client import EnableBankingClient
from src.enablebanking.tls import get_ssl_context

CONSENT_VALIDITY_DAYS = 180


def _session_file(aspsp_name: str) -> Path:
    return DATA_DIR / f"enablebanking_session_{aspsp_name.lower()}.json"


def link_account(
    aspsp_name: str,
    aspsp_country: str = "FR",
    config: Optional[EnableBankingConfig] = None,
) -> dict:
    """Runs the PSD2 consent redirect flow for one bank and stores the session."""
    config = config or load_enable_banking_config()
    client = EnableBankingClient(config)

    port = urllib.parse.urlparse(config.redirect_uri).port
    state = secrets.token_urlsafe(24)
    valid_until = (
        datetime.now(timezone.utc) + timedelta(days=CONSENT_VALIDITY_DAYS)
    ).isoformat()

    auth_response = client.start_auth(
        aspsp_name=aspsp_name,
        aspsp_country=aspsp_country,
        redirect_url=config.redirect_uri,
        state=state,
        valid_until=valid_until,
    )

    print(f"Opening browser for {aspsp_name} consent...")
    print(f"If it doesn't open automatically, visit:\n{auth_response['url']}\n")
    webbrowser.open(auth_response["url"])

    params = listen_for_callback(port, ssl_context=get_ssl_context())

    if "error" in params:
        raise RuntimeError(f"{aspsp_name} authorization failed: {params}")
    if params.get("state", [None])[0] != state:
        raise RuntimeError("State mismatch on OAuth callback - possible CSRF, aborting.")
    code = params.get("code", [None])[0]
    if not code:
        raise RuntimeError(f"No authorization code in callback: {params}")

    session = client.create_session(code)
    _session_file(aspsp_name).write_text(json.dumps(session, indent=2))
    print(f"{aspsp_name} linked, session saved to {_session_file(aspsp_name)}")
    return session


def load_session(aspsp_name: str) -> dict:
    path = _session_file(aspsp_name)
    if not path.is_file():
        raise RuntimeError(f"No stored session for {aspsp_name}, run link_account() first.")
    return json.loads(path.read_text())


if __name__ == "__main__":
    bank = sys.argv[1] if len(sys.argv) > 1 else "LCL"
    link_account(bank)
