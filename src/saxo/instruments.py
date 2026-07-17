"""Fetches Saxo position + instrument details for the ETF portfolio."""

from typing import List

from src.saxo.client import SaxoClient


def fetch_etf_holdings(client: SaxoClient) -> List[dict]:
    """Returns one entry per open ETF position: symbol, description, an
    approximate EUR value, and unrealized P&L.

    Saxo's live price endpoints return "NoAccess" for this read-only app (no
    market data entitlement), so MarketValueOpenInBaseCurrency (the value at
    the time each position was opened, i.e. cost basis) is used as a
    stand-in for current market value in value_eur - a reasonable proxy, but
    not live. ProfitLossOnTradeInBaseCurrency, however, is Saxo's own
    server-side computed unrealized P&L and stays accurate even without a
    live price entitlement, so pnl_eur/pnl_pct/current_value_eur are exact.
    """
    positions = client.get("port/v1/positions/me")
    holdings = []

    for p in positions["Data"]:
        base = p["PositionBase"]
        if base.get("AssetType") != "Etf":
            continue
        details = client.get(f"ref/v1/instruments/details/{base['Uic']}/Etf")
        view = p["PositionView"]
        cost_basis = abs(view["MarketValueOpenInBaseCurrency"])
        pnl_eur = view["ProfitLossOnTradeInBaseCurrency"]
        holdings.append(
            {
                "uic": base["Uic"],
                "symbol": details.get("Symbol"),
                "description": details.get("Description"),
                "amount": base["Amount"],
                "value_eur": cost_basis,
                "pnl_eur": pnl_eur,
                "pnl_pct": (pnl_eur / cost_basis * 100) if cost_basis else 0.0,
                "current_value_eur": cost_basis + pnl_eur,
            }
        )

    return holdings
