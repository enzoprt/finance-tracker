"""Builds the single consolidated data/summary.json the dashboard reads.

Fetches everything once (Saxo, LCL, N26) and runs every report module
against that one fetch, to avoid hammering the Enable Banking API with
redundant calls across separate scripts.

Usage:
    python -m scripts.build_summary                          # since account creation
    python -m scripts.build_summary 2024-04-01 2026-07-15    # custom performance window
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.anomalies import build_anomaly_report  # noqa: E402
from src.benchmark import fetch_benchmark_history, fetch_benchmark_return  # noqa: E402
from src.config import DATA_DIR, load_account_holder_surname  # noqa: E402
from src.enablebanking.auth import load_session  # noqa: E402
from src.enablebanking.client import EnableBankingClient  # noqa: E402
from src.enablebanking.normalize import normalize_transactions, pick_current_balance  # noqa: E402
from src.etf_allocation import build_etf_allocation_report  # noqa: E402
from src.fees import build_fee_report  # noqa: E402
from src.fx_cost import build_fx_cost_report  # noqa: E402
from src.livrets import load_config as load_livret_config  # noqa: E402
from src.livrets import reconcile_livrets  # noqa: E402
from src.model import Transaction  # noqa: E402
from src.networth import build_net_worth  # noqa: E402
from src.performance import compute_xirr  # noqa: E402
from src.saxo.client import SaxoClient  # noqa: E402
from src.saxo.instruments import fetch_etf_holdings  # noqa: E402
from src.saxo.normalize import normalize_trades  # noqa: E402
from src.saxo.performance import fetch_performance_timeseries  # noqa: E402
from src.spending import build_cashflow_report  # noqa: E402

SUMMARY_FILE = DATA_DIR / "summary.json"
NET_WORTH_HISTORY_FILE = DATA_DIR / "net_worth_history.json"
ETF_ALLOCATION_HISTORY_FILE = DATA_DIR / "etf_allocation_history.json"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"


def _cached_transactions_for(account_label: str) -> list:
    if not TRANSACTIONS_FILE.is_file():
        return []
    cached = json.loads(TRANSACTIONS_FILE.read_text())
    return [Transaction(**t) for t in cached if t["account"] == account_label]


def _cached_balance_for(account_label: str) -> dict:
    if not NET_WORTH_HISTORY_FILE.is_file():
        return {"amount": 0.0, "currency": "EUR"}
    history = json.loads(NET_WORTH_HISTORY_FILE.read_text())
    last = history[-1]["accounts"].get(account_label, 0.0) if history else 0.0
    return {"amount": last, "currency": "EUR"}


def main() -> None:
    surname = load_account_holder_surname()
    eb_client = EnableBankingClient()
    saxo_client = SaxoClient()
    saxo_accounts = saxo_client.accounts_me()["Data"]

    # Default the performance window to since-account-creation rather than a
    # fixed rolling 365 days: a buy-and-hold investor with no recent cash
    # movement can have zero cash-transfer activity in a short window, which
    # makes Saxo's performance API return an empty series entirely (not just
    # a flat one) - "no activity in the last 12 months" then wrongly reads as
    # "no performance to show" even with years of real gains behind it.
    earliest_creation = min(a["CreationDate"][:10] for a in saxo_accounts)
    perf_from = sys.argv[1] if len(sys.argv) > 1 else earliest_creation
    perf_to = sys.argv[2] if len(sys.argv) > 2 else str(date.today())

    # --- Fetch everything once ---
    all_transactions = []
    bank_balances = {}
    for bank, label in (("LCL", "LCL Compte Courant"), ("N26", "N26")):
        session = load_session(bank)
        account = session["accounts"][0]
        try:
            raw = eb_client.get_transactions(account["uid"])["transactions"]
            all_transactions += normalize_transactions(bank, label, raw, surname)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 429:
                raise
            cached = _cached_transactions_for(label)
            print(f"{label}: rate-limited, reusing {len(cached)} cached transaction(s)")
            all_transactions += cached

        try:
            bank_balances[label] = pick_current_balance(eb_client.get_balances(account["uid"]))
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 429:
                raise
            bank_balances[label] = _cached_balance_for(label)
            print(f"{label}: rate-limited, reusing last known balance from net worth history")

    client_key = saxo_accounts[0]["ClientKey"]
    trades = saxo_client.get(
        f"cs/v1/reports/trades/{client_key}",
        params={"FromDate": perf_from, "ToDate": perf_to},
    )["Data"]
    all_transactions += normalize_trades("Saxo", trades)

    saxo_balance = saxo_client.get("port/v1/balances/me")
    etf_holdings = fetch_etf_holdings(saxo_client)

    # --- Livrets ---
    livret_config = load_livret_config()
    livret_result = reconcile_livrets(all_transactions, livret_config)

    # --- Net worth ---
    net_worth = build_net_worth(
        saxo_total_value=saxo_balance["TotalValue"],
        saxo_currency=saxo_balance["Currency"],
        lcl_balance=bank_balances["LCL Compte Courant"]["amount"],
        lcl_currency=bank_balances["LCL Compte Courant"]["currency"],
        n26_balance=bank_balances["N26"]["amount"],
        n26_currency=bank_balances["N26"]["currency"],
        livret_balances=livret_result["balances"],
    )
    history = (
        json.loads(NET_WORTH_HISTORY_FILE.read_text()) if NET_WORTH_HISTORY_FILE.is_file() else []
    )
    history = [h for h in history if h["date"] != net_worth["date"]]
    history.append(net_worth)
    NET_WORTH_HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    # --- Performance ---
    perf = fetch_performance_timeseries(saxo_client, client_key, perf_from, perf_to)
    cash_transfers = perf["Balance"]["CashTransfer"]
    account_values = perf["Balance"]["AccountValue"]
    twr_points = perf["TimeWeighted"]["Accumulated"]

    if account_values and any(p["Value"] for p in cash_transfers):
        final_value = account_values[-1]["Value"]
        final_date = account_values[-1]["Date"]
        benchmark = fetch_benchmark_return(perf_from, perf_to)
        benchmark_series = fetch_benchmark_history(perf_from, perf_to)
        benchmark_by_date = {p["date"]: p["value"] for p in benchmark_series}

        dates = [p["Date"] for p in twr_points]
        performance = {
            "from_date": perf_from,
            "to_date": perf_to,
            "final_portfolio_value": final_value,
            "xirr": round(compute_xirr(cash_transfers, final_value, final_date), 4),
            "twr": round(twr_points[-1]["Value"], 4) if twr_points else None,
            "benchmark": benchmark,
            "series": {
                "dates": dates,
                "portfolio_twr": [round(p["Value"], 6) for p in twr_points],
                "account_value": [p["Value"] for p in account_values],
                "benchmark_return": [benchmark_by_date.get(d) for d in dates],
            },
        }
    else:
        performance = {"from_date": perf_from, "to_date": perf_to, "status": "no_activity"}

    # --- Other reports (reuse the transactions fetched above) ---
    fee_report = build_fee_report(all_transactions)
    cashflow_report = build_cashflow_report(all_transactions)
    fx_cost_report = build_fx_cost_report(all_transactions)
    anomaly_report = build_anomaly_report(all_transactions)
    etf_allocation_report = build_etf_allocation_report(etf_holdings)

    allocation_snapshot = {
        "date": net_worth["date"],
        "total_value_eur": etf_allocation_report["total_value_eur"],
        "by_geography_pct": etf_allocation_report["by_geography_pct"],
        "by_sector_pct": etf_allocation_report["by_sector_pct"],
    }
    allocation_history = (
        json.loads(ETF_ALLOCATION_HISTORY_FILE.read_text())
        if ETF_ALLOCATION_HISTORY_FILE.is_file()
        else []
    )
    allocation_history = [h for h in allocation_history if h["date"] != allocation_snapshot["date"]]
    allocation_history.append(allocation_snapshot)
    ETF_ALLOCATION_HISTORY_FILE.write_text(json.dumps(allocation_history, indent=2, ensure_ascii=False))
    etf_allocation_report["history"] = allocation_history

    bank_transactions = [t.to_dict() for t in all_transactions if t.account != "Saxo"]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "net_worth": net_worth,
        "net_worth_history": history,
        "performance": performance,
        "fees": fee_report,
        "cash_flow": cashflow_report,
        "fx_cost": fx_cost_report,
        "anomalies": anomaly_report,
        "etf_allocation": etf_allocation_report,
        "transactions": bank_transactions,
    }

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Summary written to {SUMMARY_FILE}")
    print(f"Net worth: {net_worth['total_eur']:,.2f} EUR")

    if livret_result["pending_count"]:
        print(
            f"\n{livret_result['pending_count']} internal transfer(s) need a livret "
            f"assignment - edit data/livret_assignments.json and re-run."
        )


if __name__ == "__main__":
    main()
