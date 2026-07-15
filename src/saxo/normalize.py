"""Normalizes Saxo trade history into the unified schema.

Saxo trades don't carry a separate commission/fee line in this report; fee
tracking for Saxo (trading commissions, custody fees) will use dedicated
cost fields once there is real trading activity to inspect.
"""

from typing import List

from src.model import CATEGORY_TRADE, Transaction


def normalize_trades(account_label: str, raw_trades: list) -> List[Transaction]:
    transactions = []
    for trade in raw_trades:
        transactions.append(
            Transaction(
                date=trade["TradeDate"],
                account=account_label,
                amount=float(trade["Amount"]),
                currency=trade["AccountCurrency"],
                category=CATEGORY_TRADE,
                description=f"{trade['TradeEventType']} {trade['InstrumentSymbol']} ({trade['InstrumentDescription']})",
                is_fee=False,
            )
        )
    return transactions
