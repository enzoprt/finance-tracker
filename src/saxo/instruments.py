"""Fetches Saxo position + instrument details for the ETF portfolio."""

from typing import List

from src.saxo.client import SaxoClient


def fetch_etf_holdings(client: SaxoClient) -> List[dict]:
    """Returns one entry per open ETF position: symbol, description, and an
    approximate EUR value.

    Saxo's live price endpoints return "NoAccess" for this read-only app (no
    market data entitlement), so MarketValueOpenInBaseCurrency (the value at
    the time each position was opened) is used as a stand-in for current
    market value - a reasonable proxy, but not live.
    """
    positions = client.get("port/v1/positions/me")
    holdings = []

    for p in positions["Data"]:
        base = p["PositionBase"]
        if base.get("AssetType") != "Etf":
            continue
        details = client.get(f"ref/v1/instruments/details/{base['Uic']}/Etf")
        holdings.append(
            {
                "uic": base["Uic"],
                "symbol": details.get("Symbol"),
                "description": details.get("Description"),
                "amount": base["Amount"],
                "value_eur": abs(p["PositionView"]["MarketValueOpenInBaseCurrency"]),
            }
        )

    return holdings
