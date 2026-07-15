"""Lists French ASPSPs known to Enable Banking, to find the exact names for
LCL and N26 before building the consent flow.

Usage:
    python -m scripts.list_aspsps_fr
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.enablebanking.client import EnableBankingClient  # noqa: E402


def main() -> None:
    client = EnableBankingClient()
    aspsps = client.list_aspsps(country="FR")
    matches = [a for a in aspsps if "lcl" in a["name"].lower() or "n26" in a["name"].lower()]
    print(f"{len(aspsps)} ASPSPs found for FR, {len(matches)} matching LCL/N26:\n")
    for a in matches:
        print(a)


if __name__ == "__main__":
    main()
