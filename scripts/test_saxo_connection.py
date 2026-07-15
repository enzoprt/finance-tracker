"""Runs the Saxo login flow (if needed) and prints the logged-in accounts.

Usage:
    python -m scripts.test_saxo_connection
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.saxo.client import SaxoClient  # noqa: E402


def main() -> None:
    client = SaxoClient()
    accounts = client.accounts_me()
    print(json.dumps(accounts, indent=2))


if __name__ == "__main__":
    main()
