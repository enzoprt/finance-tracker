"""Flags unusual fees, duplicate-looking transactions, and outsized charges."""

from datetime import date
from statistics import median
from typing import List

from src.model import CATEGORY_SPENDING, Transaction

LARGE_FEE_THRESHOLD_EUR = 20.0
DUPLICATE_WINDOW_DAYS = 2
DUPLICATE_DESCRIPTION_PREFIX_LEN = 20
OUTLIER_MULTIPLIER = 5
OUTLIER_MIN_AMOUNT_EUR = 50.0


def _dates_close(date_a: str, date_b: str, days: int) -> bool:
    return abs((date.fromisoformat(date_a) - date.fromisoformat(date_b)).days) <= days


def find_large_fees(transactions: List[Transaction]) -> list:
    return [
        {
            "date": t.date,
            "account": t.account,
            "amount": t.amount,
            "description": t.description,
            "fee_type": t.fee_type,
        }
        for t in transactions
        if t.is_fee and abs(t.amount) >= LARGE_FEE_THRESHOLD_EUR
    ]


def find_duplicate_transactions(transactions: List[Transaction]) -> list:
    duplicates = []
    seen: List[Transaction] = []

    for t in transactions:
        prefix = t.description[:DUPLICATE_DESCRIPTION_PREFIX_LEN].lower()
        for other in seen:
            other_prefix = other.description[:DUPLICATE_DESCRIPTION_PREFIX_LEN].lower()
            if (
                t.account == other.account
                and t.currency == other.currency
                and abs(t.amount - other.amount) < 0.01
                and prefix == other_prefix
                and _dates_close(t.date, other.date, DUPLICATE_WINDOW_DAYS)
            ):
                duplicates.append(
                    {
                        "account": t.account,
                        "amount": t.amount,
                        "description": t.description,
                        "date_a": other.date,
                        "date_b": t.date,
                    }
                )
        seen.append(t)

    return duplicates


def find_outlier_spending(transactions: List[Transaction]) -> list:
    spending = [t for t in transactions if t.category == CATEGORY_SPENDING]
    if len(spending) < 5:
        return []

    typical = median(abs(t.amount) for t in spending)
    threshold = max(typical * OUTLIER_MULTIPLIER, OUTLIER_MIN_AMOUNT_EUR)

    return [
        {"date": t.date, "account": t.account, "amount": t.amount, "description": t.description}
        for t in spending
        if abs(t.amount) >= threshold
    ]


def build_anomaly_report(transactions: List[Transaction]) -> dict:
    return {
        "large_fees": find_large_fees(transactions),
        "possible_duplicates": find_duplicate_transactions(transactions),
        "outlier_spending": find_outlier_spending(transactions),
    }
