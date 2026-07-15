"""Consolidated net worth across Saxo, LCL, N26, and the manually-tracked
Livrets, converted to EUR (frankfurter.app / ECB rates).
"""

from datetime import date
from typing import Optional

from src.fx import convert


def build_net_worth(
    saxo_total_value: float,
    saxo_currency: str,
    lcl_balance: float,
    lcl_currency: str,
    n26_balance: float,
    n26_currency: str,
    livret_balances: dict,
    as_of: Optional[str] = None,
) -> dict:
    as_of = as_of or str(date.today())

    accounts = {
        "Saxo": convert(saxo_total_value, saxo_currency, "EUR"),
        "LCL Compte Courant": convert(lcl_balance, lcl_currency, "EUR"),
        "N26": convert(n26_balance, n26_currency, "EUR"),
        **livret_balances,
    }
    total = sum(accounts.values())

    return {
        "date": as_of,
        "accounts": {k: round(v, 2) for k, v in accounts.items()},
        "total_eur": round(total, 2),
    }
