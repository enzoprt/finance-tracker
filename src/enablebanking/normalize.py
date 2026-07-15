"""Normalizes Enable Banking (LCL, N26) transactions into the unified schema.

Fee keywords per bank:
- LCL: French banking vocabulary (COTISATION, FRAIS, AGIOS, COMMISSION).
- N26: their transaction descriptions are in English and consistently
  contain "Fee" (e.g. "Additional Card Fee", foreign transaction mark-up).

Internal transfers (e.g. towards a Livret, which is outside PSD2 scope and
never directly visible) are detected heuristically: a transfer-type
transaction (label starts with VIR/VIREMENT) whose remittance text contains
the account holder's own surname is almost certainly money moving between
the user's own accounts, not a payment to/from someone else.
"""

from typing import List

from src.model import (
    CATEGORY_FEE,
    CATEGORY_INCOME,
    CATEGORY_INTERNAL_TRANSFER,
    CATEGORY_SPENDING,
    Transaction,
)

LCL_FEE_KEYWORDS = ("COTISATION", "FRAIS", "AGIOS", "COMMISSION")
N26_FEE_KEYWORDS = ("FEE",)
TRANSFER_PREFIXES = ("VIR", "VIREMENT")

LCL_FEE_TYPES = (
    ("COTISATION", "card_subscription"),
    ("AGIOS", "overdraft_interest"),
    ("COMMISSION", "commission"),
    ("FRAIS", "bank_fee"),
)
N26_FEE_TYPES = (
    ("FOREIGN", "foreign_transaction_fee"),
    ("WITHDRAWAL", "withdrawal_fee"),
    ("ATM", "withdrawal_fee"),
    ("CARD", "card_fee"),
)


def _remittance_text(txn: dict) -> str:
    return " ".join(txn.get("remittance_information") or [])


def _is_fee(aspsp_name: str, text: str) -> bool:
    keywords = LCL_FEE_KEYWORDS if aspsp_name == "LCL" else N26_FEE_KEYWORDS
    text_upper = text.upper()
    return any(keyword in text_upper for keyword in keywords)


def _fee_type(aspsp_name: str, text: str) -> str:
    text_upper = text.upper()
    rules = LCL_FEE_TYPES if aspsp_name == "LCL" else N26_FEE_TYPES
    for keyword, fee_type in rules:
        if keyword in text_upper:
            return fee_type
    return "other_fee"


BALANCE_TYPE_PRIORITY = ("XPCD", "CLBD")


def pick_current_balance(balances_response: dict) -> dict:
    """Picks the most current balance from a GET .../balances response
    (XPCD "expected" balance if present, else CLBD "closing booked", else
    whatever's first). Returns {"amount": float, "currency": str}.
    """
    balances = balances_response["balances"]
    by_type = {b["balance_type"]: b for b in balances}
    for balance_type in BALANCE_TYPE_PRIORITY:
        if balance_type in by_type:
            chosen = by_type[balance_type]
            break
    else:
        chosen = balances[0]
    return {
        "amount": float(chosen["balance_amount"]["amount"]),
        "currency": chosen["balance_amount"]["currency"],
    }


def _is_self_transfer(text: str, account_holder_surname: str) -> bool:
    first_line = (text.splitlines()[0] if text else "").strip().upper()
    is_transfer = first_line.startswith(TRANSFER_PREFIXES)
    return is_transfer and account_holder_surname.upper() in text.upper()


def normalize_transactions(
    aspsp_name: str,
    account_label: str,
    raw_transactions: list,
    account_holder_surname: str,
) -> List[Transaction]:
    transactions = []
    for txn in raw_transactions:
        text = _remittance_text(txn)
        amount = float(txn["transaction_amount"]["amount"])
        signed_amount = amount if txn["credit_debit_indicator"] == "CRDT" else -amount

        is_fee = _is_fee(aspsp_name, text)
        fee_type = _fee_type(aspsp_name, text) if is_fee else None
        if is_fee:
            category = CATEGORY_FEE
        elif _is_self_transfer(text, account_holder_surname):
            category = CATEGORY_INTERNAL_TRANSFER
        elif signed_amount > 0:
            category = CATEGORY_INCOME
        else:
            category = CATEGORY_SPENDING

        transactions.append(
            Transaction(
                date=txn["booking_date"],
                account=account_label,
                amount=signed_amount,
                currency=txn["transaction_amount"]["currency"],
                category=category,
                description=" ".join(text.split()) or "(no description)",
                is_fee=is_fee,
                fee_type=fee_type,
            )
        )
    return transactions
