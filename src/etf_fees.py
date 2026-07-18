"""ETF-level ongoing charges (TER) and a rough post-tax value estimate.

TER (Total Expense Ratio, aka OCF) is deducted from a fund's NAV daily by
the fund manager - it is never billed to the investor as a separate
transaction, and it is already fully reflected in the price/performance
shown everywhere else in this app (the Performance tab's TWR, Saxo's own
valuations). This module exists to make that invisible drag visible, and
is deliberately distinct from src/fees.py, which tracks broker/bank fees
(commissions, FX markup) that are real, separate, out-of-pocket costs -
NOT absorbed anywhere.
"""

from typing import List, Optional

# France's flat tax ("PFU" / prelevement forfaitaire unique) on capital
# gains in a taxable brokerage account (CTO): 12.8% income tax + 17.2%
# social contributions = 30% combined. Applied here to every holding
# because the PEA and PEA-PME are both currently empty (see the AI
# Overview's tax-wrapper finding) - all 20 positions sit in the taxable
# CTO today. Revisit this constant if future purchases start routing into
# the PEA, where gains are exempt from the income-tax portion after 5 years.
FRENCH_CTO_FLAT_TAX_RATE = 0.30


def build_etf_fees_report(holdings: List[dict], ter_by_symbol: dict) -> dict:
    """holdings: fetch_etf_holdings() output (value_eur, pnl_eur,
    current_value_eur per fund). ter_by_symbol: from
    build_lookthrough_report()'s "ter_by_symbol", reusing the TER already
    read off the same funds_data fetch - no extra network call here."""
    total_value = sum(h["value_eur"] for h in holdings)
    known_value = 0.0
    annual_cost_eur = 0.0
    total_post_tax_value = 0.0
    by_fund = []

    for h in holdings:
        ter: Optional[float] = ter_by_symbol.get(h["symbol"])
        pnl = h.get("pnl_eur", 0.0)
        tax_owed = pnl * FRENCH_CTO_FLAT_TAX_RATE if pnl > 0 else 0.0
        current_value = h.get("current_value_eur", h["value_eur"])
        post_tax_value = current_value - tax_owed
        total_post_tax_value += post_tax_value

        fund_annual_cost = h["value_eur"] * ter if ter is not None else None
        by_fund.append(
            {
                "symbol": h["symbol"],
                "description": h["description"],
                "value_eur": round(h["value_eur"], 2),
                "ter_pct": round(ter * 100, 2) if ter is not None else None,
                "annual_cost_eur": round(fund_annual_cost, 2) if fund_annual_cost is not None else None,
                "post_tax_value_eur": round(post_tax_value, 2),
            }
        )
        if ter is not None:
            known_value += h["value_eur"]
            annual_cost_eur += fund_annual_cost

    weighted_avg_ter_pct = round(annual_cost_eur / known_value * 100, 2) if known_value else None

    return {
        "by_fund": sorted(by_fund, key=lambda f: -(f["annual_cost_eur"] or 0)),
        "weighted_avg_ter_pct": weighted_avg_ter_pct,
        "annual_cost_eur": round(annual_cost_eur, 2),
        "ter_coverage_pct": round(known_value / total_value * 100, 1) if total_value else 0.0,
        "total_value_eur": round(total_value, 2),
        "total_post_tax_value_eur": round(total_post_tax_value, 2),
        "flat_tax_rate_pct": round(FRENCH_CTO_FLAT_TAX_RATE * 100, 1),
    }
