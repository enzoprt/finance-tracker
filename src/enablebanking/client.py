"""Thin authenticated HTTP client for the Enable Banking API."""

from typing import Optional

import requests

from src.config import EnableBankingConfig, load_enable_banking_config
from src.enablebanking.jwt_auth import get_application_jwt


class EnableBankingClient:
    def __init__(self, config: Optional[EnableBankingConfig] = None):
        self.config = config or load_enable_banking_config()

    def _headers(self) -> dict:
        token = get_application_jwt(self.config)
        return {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        response = requests.get(
            f"{self.config.api_base_url}/{path.lstrip('/')}",
            headers=self._headers(),
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, json_body: dict) -> dict:
        response = requests.post(
            f"{self.config.api_base_url}/{path.lstrip('/')}",
            headers=self._headers(),
            json=json_body,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def list_aspsps(self, country: str) -> list:
        return self._get("aspsps", params={"country": country}).get("aspsps", [])

    def start_auth(
        self,
        aspsp_name: str,
        aspsp_country: str,
        redirect_url: str,
        state: str,
        valid_until: str,
        psu_type: str = "personal",
    ) -> dict:
        return self._post(
            "auth",
            {
                "access": {"valid_until": valid_until},
                "aspsp": {"name": aspsp_name, "country": aspsp_country},
                "state": state,
                "redirect_url": redirect_url,
                "psu_type": psu_type,
            },
        )

    def create_session(self, code: str) -> dict:
        return self._post("sessions", {"code": code})

    def get_session(self, session_id: str) -> dict:
        return self._get(f"sessions/{session_id}")

    def get_balances(self, account_uid: str) -> dict:
        return self._get(f"accounts/{account_uid}/balances")

    def get_transactions(self, account_uid: str, continuation_key: Optional[str] = None) -> dict:
        params = {"continuation_key": continuation_key} if continuation_key else None
        return self._get(f"accounts/{account_uid}/transactions", params=params)
