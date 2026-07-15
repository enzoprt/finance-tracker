"""Reconstructs regulated-savings-account (Livret) balances.

Livrets (Livret A, Livret Jeune, LDDS, ...) are legally excluded from PSD2
scope in France, so no bank API can ever return their balance directly. The
only visible trace is the internal transfer itself, on the linked current
account (see src.enablebanking.normalize for how those are detected).

This module keeps a small user-editable JSON file (data/livret_assignments.json)
with a manual seed balance per livret plus a mapping from detected internal
transfer -> livret name. New, not-yet-assigned transfers are added to that
file with a null value; the user fills them in by hand and re-runs.
"""

import json
from typing import List

from src.config import DATA_DIR
from src.model import CATEGORY_INTERNAL_TRANSFER, Transaction

ASSIGNMENTS_FILE = DATA_DIR / "livret_assignments.json"


def _fingerprint(txn: Transaction) -> str:
    slug = "".join(c for c in txn.description[:40] if c.isalnum() or c == " ")
    slug = "_".join(slug.split())
    return f"{txn.date}_{txn.amount:+.2f}_{slug}"


def load_config() -> dict:
    if not ASSIGNMENTS_FILE.is_file():
        return {"livrets": {}, "assignments": {}}
    return json.loads(ASSIGNMENTS_FILE.read_text())


def save_config(config: dict) -> None:
    ASSIGNMENTS_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def reconcile_livrets(transactions: List[Transaction], config: dict) -> dict:
    """Returns {"balances": {name: float}, "pending_count": int}.

    Mutates and persists `config` in place: any newly seen internal
    transfer dated on/after a livret's seed date is recorded with a null
    assignment so the user can fill it in later.
    """
    livrets = config["livrets"]
    balances = {name: data["seed_balance"] for name, data in livrets.items()}
    assignments = config.setdefault("assignments", {})

    internal_transfers = [t for t in transactions if t.category == CATEGORY_INTERNAL_TRANSFER]
    pending_count = 0

    for txn in sorted(internal_transfers, key=lambda t: t.date):
        fp = _fingerprint(txn)
        livret_name = assignments.get(fp)

        if livret_name is None:
            if fp not in assignments:
                # Only worth asking about it if it happened after every
                # livret's seed date; earlier transfers are already baked
                # into the seed balance the user provided.
                if any(txn.date >= data["seed_date"] for data in livrets.values()):
                    assignments[fp] = None
            if fp in assignments:
                pending_count += 1
            continue

        if livret_name not in balances or txn.date < livrets[livret_name]["seed_date"]:
            continue

        # txn.amount is signed from the current account's point of view:
        # negative (money left checking) means the livret balance grew.
        balances[livret_name] += -txn.amount

    save_config(config)
    return {"balances": balances, "pending_count": pending_count}
