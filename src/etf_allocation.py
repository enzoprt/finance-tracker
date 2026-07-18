"""Builds the ETF portfolio allocation report: precise sector and country
exposure via src/etf_lookthrough.py (real fund data, not name-guessing),
plus the per-fund holdings/weight table.
"""

from typing import List

from src.etf_lookthrough import build_lookthrough_report


def build_etf_allocation_report(holdings: List[dict]) -> dict:
    total_value = sum(h["value_eur"] for h in holdings)

    by_fund = sorted(
        (
            {
                "symbol": h["symbol"],
                "description": h["description"],
                "value_eur": round(h["value_eur"], 2),
                "weight_pct": round(h["value_eur"] / total_value * 100, 2) if total_value else 0,
                "pnl_eur": round(h["pnl_eur"], 2),
                "pnl_pct": round(h["pnl_pct"], 2),
            }
            for h in holdings
        ),
        key=lambda f: -f["value_eur"],
    )

    lookthrough = build_lookthrough_report(holdings)

    return {
        "total_value_eur": round(total_value, 2),
        "by_fund": by_fund,
        "by_geography_pct": lookthrough["by_country_pct"],
        "by_sector_pct": lookthrough["by_sector_pct"],
        "lookthrough_errors": lookthrough["errors"],
        "ter_by_symbol": lookthrough["ter_by_symbol"],
    }
