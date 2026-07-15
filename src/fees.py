"""Fee breakdown across all linked accounts: by account, by fee type, and
over time. All fees detected so far are EUR-denominated (LCL and N26 both
report in EUR); this doesn't yet convert mixed-currency fees.
"""

from collections import defaultdict
from typing import List

from src.model import Transaction


def build_fee_report(transactions: List[Transaction]) -> dict:
    fees = [t for t in transactions if t.is_fee]

    by_account: dict = defaultdict(float)
    by_type: dict = defaultdict(float)
    by_month: dict = defaultdict(float)

    for fee in fees:
        amount = abs(fee.amount)
        by_account[fee.account] += amount
        by_type[fee.fee_type or "other_fee"] += amount
        by_month[fee.date[:7]] += amount  # YYYY-MM

    return {
        "total": round(sum(abs(fee.amount) for fee in fees), 2),
        "count": len(fees),
        "by_account": {k: round(v, 2) for k, v in sorted(by_account.items())},
        "by_type": {k: round(v, 2) for k, v in sorted(by_type.items())},
        "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
    }
