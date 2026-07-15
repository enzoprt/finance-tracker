"""Loads all credentials and settings from .env. Nothing here is hardcoded."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class SaxoConfig:
    app_key: str
    app_secret: str
    redirect_uri: str
    environment: str

    @property
    def auth_base_url(self) -> str:
        return (
            "https://sim.logonvalidation.net"
            if self.environment == "SIM"
            else "https://live.logonvalidation.net"
        )

    @property
    def api_base_url(self) -> str:
        return (
            "https://gateway.saxobank.com/sim/openapi"
            if self.environment == "SIM"
            else "https://gateway.saxobank.com/openapi"
        )


@dataclass(frozen=True)
class EnableBankingConfig:
    application_id: str
    private_key_path: Path
    redirect_uri: str
    api_base_url: str = "https://api.enablebanking.com"


def load_saxo_config() -> SaxoConfig:
    return SaxoConfig(
        app_key=_require("SAXO_APP_KEY"),
        app_secret=_require("SAXO_APP_SECRET"),
        redirect_uri=_require("SAXO_REDIRECT_URI"),
        environment=os.environ.get("SAXO_ENVIRONMENT", "SIM").upper(),
    )


def load_enable_banking_config() -> EnableBankingConfig:
    key_path = Path(_require("ENABLE_BANKING_PRIVATE_KEY_PATH")).expanduser()
    if not key_path.is_file():
        raise RuntimeError(f"Enable Banking private key not found at: {key_path}")
    return EnableBankingConfig(
        application_id=_require("ENABLE_BANKING_APPLICATION_ID"),
        private_key_path=key_path,
        redirect_uri=_require("ENABLE_BANKING_REDIRECT_URI"),
    )


def load_account_holder_surname() -> str:
    return _require("ACCOUNT_HOLDER_SURNAME")
