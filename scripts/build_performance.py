"""Builds the ETF portfolio performance report: money-weighted (XIRR) and
time-weighted (Saxo-native) return, compared against a benchmark index.
Writes data/performance_report.json.

Usage:
    python -m scripts.build_performance [FromDate] [ToDate]
    python -m scripts.build_performance 2026-01-01 2026-07-15
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.benchmark import fetch_benchmark_return  # noqa: E402
from src.config import DATA_DIR  # noqa: E402
from src.performance import compute_xirr  # noqa: E402
from src.saxo.client import SaxoClient  # noqa: E402
from src.saxo.performance import fetch_performance_timeseries  # noqa: E402

REPORT_FILE = DATA_DIR / "performance_report.json"


def main() -> None:
    from_date = sys.argv[1] if len(sys.argv) > 1 else str(date.today() - timedelta(days=365))
    to_date = sys.argv[2] if len(sys.argv) > 2 else str(date.today())

    client = SaxoClient()
    accounts = client.accounts_me()["Data"]
    if not accounts:
        print("No Saxo account found.")
        return
    client_key = accounts[0]["ClientKey"]

    perf = fetch_performance_timeseries(client, client_key, from_date, to_date)
    cash_transfers = perf["Balance"]["CashTransfer"]
    account_values = perf["Balance"]["AccountValue"]
    twr_points = perf["TimeWeighted"]["Accumulated"]

    if not account_values or not any(p["Value"] for p in cash_transfers):
        print(
            f"No real trading/cash activity on the Saxo account between "
            f"{from_date} and {to_date} yet - nothing to compute."
        )
        report = {"from_date": from_date, "to_date": to_date, "status": "no_activity"}
    else:
        final_value = account_values[-1]["Value"]
        final_date = account_values[-1]["Date"]

        xirr_result = compute_xirr(cash_transfers, final_value, final_date)
        twr_result = twr_points[-1]["Value"] if twr_points else None
        benchmark = fetch_benchmark_return(from_date, to_date)

        report = {
            "from_date": from_date,
            "to_date": to_date,
            "final_portfolio_value": final_value,
            "xirr": round(xirr_result, 4),
            "twr": round(twr_result, 4) if twr_result is not None else None,
            "benchmark": benchmark,
        }
        print(f"XIRR (money-weighted): {xirr_result * 100:.2f}%")
        print(f"TWR (time-weighted):   {twr_result * 100:.2f}%" if twr_result is not None else "TWR: n/a")
        print(f"Benchmark ({benchmark['ticker']}): {benchmark['total_return'] * 100:.2f}%")

    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written to {REPORT_FILE}")


if __name__ == "__main__":
    main()
