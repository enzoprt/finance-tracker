"""Builds the ETF geographic/sector allocation report from real Saxo
positions. Writes data/etf_allocation_report.json.

Usage:
    python -m scripts.build_etf_allocation
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR  # noqa: E402
from src.etf_allocation import build_etf_allocation_report  # noqa: E402
from src.saxo.client import SaxoClient  # noqa: E402
from src.saxo.instruments import fetch_etf_holdings  # noqa: E402

REPORT_FILE = DATA_DIR / "etf_allocation_report.json"


def main() -> None:
    client = SaxoClient()
    holdings = fetch_etf_holdings(client)

    if not holdings:
        print("No ETF positions found.")
        return

    report = build_etf_allocation_report(holdings)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"{len(holdings)} ETF holdings, {report['total_value_eur']:,.2f} EUR total (cost basis)\n")
    print("By geography:")
    for geo, pct in report["by_geography_pct"].items():
        print(f"  {geo}: {pct}%")
    print("\nBy sector:")
    for sector, pct in report["by_sector_pct"].items():
        print(f"  {sector}: {pct}%")
    print(f"\nReport written to {REPORT_FILE}")


if __name__ == "__main__":
    main()
