"""Currency conversion via the free ECB-based frankfurter.app API (no key)."""

from typing import Optional

import requests

FRANKFURTER_URL = "https://api.frankfurter.app"


def get_rate(from_currency: str, to_currency: str, on_date: Optional[str] = None) -> float:
    if from_currency == to_currency:
        return 1.0
    endpoint = on_date or "latest"
    response = requests.get(
        f"{FRANKFURTER_URL}/{endpoint}",
        params={"from": from_currency, "to": to_currency},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["rates"][to_currency]


def convert(amount: float, from_currency: str, to_currency: str, on_date: Optional[str] = None) -> float:
    return amount * get_rate(from_currency, to_currency, on_date)
