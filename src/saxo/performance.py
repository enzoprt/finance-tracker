"""Fetches Saxo's native portfolio performance report (TWR is computed
server-side by Saxo; XIRR is derived locally, see src/performance.py).
"""

from src.saxo.client import SaxoClient


def fetch_performance_timeseries(
    client: SaxoClient, client_key: str, from_date: str, to_date: str
) -> dict:
    return client.get(
        "hist/v4/performance/timeseries",
        params={"ClientKey": client_key, "FromDate": from_date, "ToDate": to_date},
    )
