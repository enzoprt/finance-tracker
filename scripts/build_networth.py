"""Builds the consolidated net worth report (Saxo LIVE + LCL + N26 +
Livrets), converted to EUR. Appends a dated snapshot to
data/net_worth_history.json for the "net worth over time" chart.

Usage:
    python -m scripts.build_networth
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, load_account_holder_surname  # noqa: E402
from src.enablebanking.auth import load_session  # noqa: E402
from src.enablebanking.client import EnableBankingClient  # noqa: E402
from src.enablebanking.normalize import normalize_transactions, pick_current_balance  # noqa: E402
from src.livrets import load_config as load_livret_config  # noqa: E402
from src.livrets import reconcile_livrets  # noqa: E402
from src.networth import build_net_worth  # noqa: E402
from src.saxo.client import SaxoClient  # noqa: E402

HISTORY_FILE = DATA_DIR / "net_worth_history.json"


def main() -> None:
    surname = load_account_holder_surname()
    eb_client = EnableBankingClient()

    saxo_client = SaxoClient()
    saxo_balance = saxo_client.get("port/v1/balances/me")

    lcl_session = load_session("LCL")
    lcl_uid = lcl_session["accounts"][0]["uid"]
    lcl_balance = pick_current_balance(eb_client.get_balances(lcl_uid))
    lcl_transactions = normalize_transactions(
        "LCL",
        "LCL Compte Courant",
        eb_client.get_transactions(lcl_uid)["transactions"],
        surname,
    )

    n26_session = load_session("N26")
    n26_uid = n26_session["accounts"][0]["uid"]
    n26_balance = pick_current_balance(eb_client.get_balances(n26_uid))

    livret_config = load_livret_config()
    livret_result = reconcile_livrets(lcl_transactions, livret_config)

    report = build_net_worth(
        saxo_total_value=saxo_balance["TotalValue"],
        saxo_currency=saxo_balance["Currency"],
        lcl_balance=lcl_balance["amount"],
        lcl_currency=lcl_balance["currency"],
        n26_balance=n26_balance["amount"],
        n26_currency=n26_balance["currency"],
        livret_balances=livret_result["balances"],
    )

    history = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.is_file() else []
    history = [h for h in history if h["date"] != report["date"]]  # replace same-day snapshot
    history.append(report)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    print(f"Net worth as of {report['date']}:")
    for account, value in report["accounts"].items():
        print(f"  {account}: {value:,.2f} EUR")
    print(f"  TOTAL: {report['total_eur']:,.2f} EUR")

    if livret_result["pending_count"]:
        print(
            f"\n{livret_result['pending_count']} internal transfer(s) need a livret "
            f"assignment - edit data/livret_assignments.json and re-run."
        )

    print(f"\nSnapshot appended to {HISTORY_FILE}")


if __name__ == "__main__":
    main()
