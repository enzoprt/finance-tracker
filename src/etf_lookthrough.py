"""Real look-through allocation for the ETF portfolio, via yfinance's fund
data - replaces the old fund-name keyword guessing with actual composition.

Sector: yfinance's `sector_weightings` covers the WHOLE fund (not just top
holdings), so this is precise, full-coverage data once weighted by each
fund's EUR value in the portfolio.

Geography: yfinance has no full country-weighting field for ETFs, only a
`top_holdings` list (typically the 10 largest positions). Country is
inferred per holding from its ticker's exchange suffix (e.g. ".DE" ->
Germany, no suffix -> United States). This only covers the fraction of
each fund actually in its top 10.

Two exceptions get 100% exact coverage with no look-through needed at all:
funds tracking a single-country/region index (S&P 500, MSCI USA, CAC 40,
FTSE India - see SINGLE_GEOGRAPHY_INDEX_KEYWORDS) are, by the index's own
legal definition, entirely composed of that country's stocks - this isn't
an approximation, it's what the index rules require. For every other
(genuinely blended, e.g. MSCI World) fund, the part of each fund beyond its
top 10 holdings is reported honestly as "Other holdings (beyond top 10 per
fund)" rather than silently dropped or guessed at, so the breakdown never
overstates its own precision.
"""

from collections import defaultdict
from typing import List, Optional

import yfinance as yf

# Ordered most-specific-first: a fund tracking one of these indices is, by
# the index's own construction rules, 100% composed of that single country's
# stocks - not an estimate. Matched against the fund's Saxo description.
SINGLE_GEOGRAPHY_INDEX_KEYWORDS = (
    ("FTSE INDIA", "India"),
    ("CAC 40", "France"),
    ("S&P 500", "United States"),
    ("MSCI USA", "United States"),
)

SAXO_EXCHANGE_TO_YAHOO_SUFFIX = {
    "xpar": "PA",
    "xetr": "DE",
    "xams": "AS",
    "xswx": "SW",
    "xlon": "L",
    "xmil": "MI",
}

STOCK_SUFFIX_TO_COUNTRY = {
    "NS": "India", "BO": "India",
    "DE": "Germany", "PA": "France", "SW": "Switzerland", "L": "United Kingdom",
    "MI": "Italy", "AS": "Netherlands", "TO": "Canada", "HK": "Hong Kong",
    "T": "Japan", "AX": "Australia", "KS": "South Korea", "SS": "China", "SZ": "China",
    "MC": "Spain", "BR": "Belgium", "ST": "Sweden", "OL": "Norway", "CO": "Denmark",
    "HE": "Finland", "VI": "Austria", "IR": "Ireland", "SA": "Brazil", "MX": "Mexico",
}

SECTOR_LABELS = {
    "realestate": "Real Estate",
    "consumer_cyclical": "Consumer Cyclical",
    "basic_materials": "Basic Materials",
    "consumer_defensive": "Consumer Defensive",
    "technology": "Technology",
    "communication_services": "Communication Services",
    "financial_services": "Financial Services",
    "utilities": "Utilities",
    "industrials": "Industrials",
    "energy": "Energy",
    "healthcare": "Healthcare",
}

OTHER_HOLDINGS_LABEL = "Other holdings (beyond top 10 per fund)"


def saxo_symbol_to_yahoo(saxo_symbol: str) -> str:
    ticker, exchange = saxo_symbol.split(":")
    suffix = SAXO_EXCHANGE_TO_YAHOO_SUFFIX.get(exchange)
    return f"{ticker}.{suffix}" if suffix else ticker


def _stock_country(stock_symbol: str) -> str:
    if "." not in stock_symbol:
        return "United States"
    suffix = stock_symbol.rsplit(".", 1)[1]
    return STOCK_SUFFIX_TO_COUNTRY.get(suffix, "Other")


def known_single_geography(description: str) -> Optional[str]:
    text_upper = description.upper()
    for keyword, country in SINGLE_GEOGRAPHY_INDEX_KEYWORDS:
        if keyword in text_upper:
            return country
    return None


def fetch_fund_ter(fund_data, yahoo_ticker: str) -> Optional[float]:
    """Annual ongoing-charges ratio ("TER") as a fraction (0.002 = 0.20%),
    read off the same funds_data object fetch_fund_lookthrough() already
    pulled sector/holdings from - no extra network call. None if missing;
    a handful of listings (seen on some Swiss/Milan tickers) return an
    implausible 0.0 rather than actually being free, so that's treated as
    missing too rather than a real value."""
    try:
        ops = fund_data.fund_operations
    except Exception:
        return None
    if ops is None or "Annual Report Expense Ratio" not in ops.index:
        return None
    ter = ops.loc["Annual Report Expense Ratio", yahoo_ticker]
    if ter is None or ter <= 0:
        return None
    return float(ter)


def fetch_fund_lookthrough(yahoo_ticker: str) -> dict:
    fund_data = yf.Ticker(yahoo_ticker).funds_data
    sector_weightings = fund_data.sector_weightings or {}
    top_holdings_df = fund_data.top_holdings

    holdings = []
    if top_holdings_df is not None and len(top_holdings_df):
        for symbol, row in top_holdings_df.iterrows():
            holdings.append({"symbol": symbol, "weight": float(row["Holding Percent"])})

    ter = fetch_fund_ter(fund_data, yahoo_ticker)
    return {"sector_weightings": sector_weightings, "top_holdings": holdings, "ter": ter}


def build_lookthrough_report(holdings: List[dict]) -> dict:
    """holdings: fetch_etf_holdings() output ([{symbol (Saxo format e.g.
    "INDW:xpar"), value_eur, ...}])."""
    sector_totals: dict = defaultdict(float)
    country_totals: dict = defaultdict(float)
    total_value = sum(h["value_eur"] for h in holdings)
    errors = []
    ter_by_symbol: dict = {}

    for h in holdings:
        fund_value = h["value_eur"]

        single_country = known_single_geography(h["description"])
        if single_country:
            country_totals[single_country] += fund_value
        try:
            data = fetch_fund_lookthrough(saxo_symbol_to_yahoo(h["symbol"]))
        except Exception as e:
            errors.append({"symbol": h["symbol"], "error": str(e)})
            sector_totals["Unknown"] += fund_value
            if not single_country:
                country_totals[OTHER_HOLDINGS_LABEL] += fund_value
            continue

        ter_by_symbol[h["symbol"]] = data["ter"]

        if data["sector_weightings"]:
            for sector, weight in data["sector_weightings"].items():
                sector_totals[SECTOR_LABELS.get(sector, sector)] += fund_value * weight
        else:
            sector_totals["Unknown"] += fund_value

        if not single_country:
            top10_weight_sum = 0.0
            for holding in data["top_holdings"]:
                country_totals[_stock_country(holding["symbol"])] += fund_value * holding["weight"]
                top10_weight_sum += holding["weight"]
            country_totals[OTHER_HOLDINGS_LABEL] += fund_value * (1 - top10_weight_sum)

    def to_pct(totals: dict) -> dict:
        return (
            {k: round(v / total_value * 100, 2) for k, v in sorted(totals.items(), key=lambda kv: -kv[1])}
            if total_value
            else {}
        )

    return {
        "by_sector_pct": to_pct(sector_totals),
        "by_country_pct": to_pct(country_totals),
        "errors": errors,
        "ter_by_symbol": ter_by_symbol,
    }
