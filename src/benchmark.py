"""Fetches historical benchmark prices via yfinance (free, no API key) and
computes the equivalent buy-and-hold return over a period, for comparison
against the Saxo portfolio's XIRR/TWR.

Default benchmark: iShares Core MSCI World UCITS ETF (IWDA.AS), a common
EUR-denominated global equity reference. Override with any yfinance ticker
once real holdings make a more specific benchmark relevant.
"""

import yfinance as yf

DEFAULT_BENCHMARK_TICKER = "IWDA.AS"


def fetch_benchmark_return(from_date: str, to_date: str, ticker: str = DEFAULT_BENCHMARK_TICKER) -> dict:
    history = yf.Ticker(ticker).history(start=from_date, end=to_date, auto_adjust=True)
    if history.empty:
        raise RuntimeError(f"No price history for {ticker} between {from_date} and {to_date}")

    start_price = float(history["Close"].iloc[0])
    end_price = float(history["Close"].iloc[-1])
    total_return = end_price / start_price - 1

    return {
        "ticker": ticker,
        "from_date": str(history.index[0].date()),
        "to_date": str(history.index[-1].date()),
        "start_price": round(start_price, 4),
        "end_price": round(end_price, 4),
        "total_return": round(total_return, 4),
    }


def fetch_benchmark_history(from_date: str, to_date: str, ticker: str = DEFAULT_BENCHMARK_TICKER) -> list:
    """Daily cumulative return series (fraction, 0 at the first trading day),
    for charting the benchmark alongside the portfolio's TWR over time.
    """
    history = yf.Ticker(ticker).history(start=from_date, end=to_date, auto_adjust=True)
    if history.empty:
        return []

    start_price = float(history["Close"].iloc[0])
    return [
        {"date": str(idx.date()), "value": round(float(price) / start_price - 1, 6)}
        for idx, price in history["Close"].items()
    ]
