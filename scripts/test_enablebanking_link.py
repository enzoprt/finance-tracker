"""Runs the Enable Banking consent flow for a given bank and prints balances.

Usage:
    python -m scripts.test_enablebanking_link LCL
    python -m scripts.test_enablebanking_link N26
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.enablebanking.auth import link_account  # noqa: E402
from src.enablebanking.client import EnableBankingClient  # noqa: E402


def main() -> None:
    bank = sys.argv[1] if len(sys.argv) > 1 else "LCL"
    session = link_account(bank, aspsp_country="FR")
    print(json.dumps(session, indent=2))

    client = EnableBankingClient()
    for account in session.get("accounts", []):
        uid = account["uid"]
        print(f"\n--- Balances for account {uid} ---")
        balances = client.get_balances(uid)
        print(json.dumps(balances, indent=2))


if __name__ == "__main__":
    main()
