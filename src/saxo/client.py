"""Thin authenticated HTTP client for the Saxo OpenAPI."""

from typing import Optional

import requests

from src.config import SaxoConfig, load_saxo_config
from src.saxo.auth import get_valid_access_token


class SaxoClient:
    def __init__(self, config: Optional[SaxoConfig] = None):
        self.config = config or load_saxo_config()

    def _headers(self) -> dict:
        token = get_valid_access_token(self.config)
        return {"Authorization": f"Bearer {token}"}

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        response = requests.get(
            f"{self.config.api_base_url}/{path.lstrip('/')}",
            headers=self._headers(),
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def accounts_me(self) -> dict:
        return self.get("port/v1/accounts/me")
