"""Builds the unified transaction list from Saxo, LCL, and N26, and
reconciles Livret balances. Writes data/transactions.json.

Usage:
    python -m scripts.build_transactions
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.anomalies import build_anomaly_report  # noqa: E402
from src.config import DATA_DIR, load_account_holder_surname  # noqa: E402
from src.enablebanking.auth import load_session  # noqa: E402
from src.enablebanking.client import EnableBankingClient  # noqa: E402
from src.enablebanking.normalize import normalize_transactions  # noqa: E402
from src.fees import build_fee_report  # noqa: E402
from src.fx_cost import build_fx_cost_report  # noqa: E402
from src.livrets import load_config as load_livret_config  # noqa: E402
from src.livrets import reconcile_livrets  # noqa: E402
from src.saxo.client import SaxoClient  # noqa: E402
from src.saxo.normalize import normalize_trades  # noqa: E402
from src.spending import build_cashflow_report  # noqa: E402

TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
FEE_REPORT_FILE = DATA_DIR / "fee_report.json"
CASHFLOW_REPORT_FILE = DATA_DIR / "cashflow_report.json"
FX_COST_REPORT_FILE = DATA_DIR / "fx_cost_report.json"
ANOMALY_REPORT_FILE = DATA_DIR / "anomaly_report.json"


def main() -> None:
    surname = load_account_holder_surname()
    eb_client = EnableBankingClient()
    all_transactions = []

    for bank, label in (("LCL", "LCL Compte Courant"), ("N26", "N26")):
        session = load_session(bank)
        for account in session["accounts"]:
            raw = eb_client.get_transactions(account["uid"])["transactions"]
            all_transactions += normalize_transactions(bank, label, raw, surname)

    saxo_client = SaxoClient()
    saxo_accounts = saxo_client.accounts_me()["Data"]
    if saxo_accounts:
        client_key = saxo_accounts[0]["ClientKey"]
        trades = saxo_client.get(
            f"cs/v1/reports/trades/{client_key}",
            params={
                "FromDate": str(date.today() - timedelta(days=730)),
                "ToDate": str(date.today()),
            },
        )["Data"]
        all_transactions += normalize_trades("Saxo", trades)

    livret_config = load_livret_config()
    livret_result = reconcile_livrets(all_transactions, livret_config)

    TRANSACTIONS_FILE.write_text(
        json.dumps([t.to_dict() for t in all_transactions], indent=2, ensure_ascii=False)
    )

    print(f"{len(all_transactions)} transactions written to {TRANSACTIONS_FILE}")
    print("\nLivret balances:")
    for name, balance in livret_result["balances"].items():
        print(f"  {name}: {balance:.2f} EUR")
    if livret_result["pending_count"]:
        print(
            f"\n{livret_result['pending_count']} internal transfer(s) need a livret "
            f"assignment - edit data/livret_assignments.json and re-run."
        )

    fee_report = build_fee_report(all_transactions)
    FEE_REPORT_FILE.write_text(json.dumps(fee_report, indent=2, ensure_ascii=False))

    print(f"\n{fee_report['count']} fee(s) detected, {fee_report['total']:.2f} EUR total")
    print(f"Report written to {FEE_REPORT_FILE}")
    print("By account:", fee_report["by_account"])
    print("By type:", fee_report["by_type"])
    print("By month:", fee_report["by_month"])

    cashflow_report = build_cashflow_report(all_transactions)
    CASHFLOW_REPORT_FILE.write_text(json.dumps(cashflow_report, indent=2, ensure_ascii=False))

    print(f"\nCash flow report written to {CASHFLOW_REPORT_FILE}")
    print("Monthly:", cashflow_report["monthly"])
    print("Spending by type:", cashflow_report["spending_by_type"])

    fx_cost_report = build_fx_cost_report(all_transactions)
    FX_COST_REPORT_FILE.write_text(json.dumps(fx_cost_report, indent=2, ensure_ascii=False))

    print(f"\nFX cost report written to {FX_COST_REPORT_FILE}")
    print(
        f"{len(fx_cost_report['transactions'])} foreign-currency transaction(s), "
        f"average markup vs ECB: {fx_cost_report['average_markup_pct']}%"
    )

    anomaly_report = build_anomaly_report(all_transactions)
    ANOMALY_REPORT_FILE.write_text(json.dumps(anomaly_report, indent=2, ensure_ascii=False))

    print(f"\nAnomaly report written to {ANOMALY_REPORT_FILE}")
    print(f"Large fees: {len(anomaly_report['large_fees'])}")
    print(f"Possible duplicates: {len(anomaly_report['possible_duplicates'])}")
    print(f"Outlier spending: {len(anomaly_report['outlier_spending'])}")


if __name__ == "__main__":
    main()
