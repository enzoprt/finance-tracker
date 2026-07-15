"""Unified transaction schema shared across Saxo, LCL, and N26."""

from dataclasses import asdict, dataclass
from typing import Optional

CATEGORY_INCOME = "income"
CATEGORY_SPENDING = "spending"
CATEGORY_FEE = "fee"
CATEGORY_INTERNAL_TRANSFER = "internal_transfer"
CATEGORY_TRADE = "trade"


@dataclass
class Transaction:
    date: str  # ISO date (YYYY-MM-DD)
    account: str  # e.g. "LCL Compte Courant", "N26", "Saxo"
    amount: float  # signed: positive = money in, negative = money out
    currency: str
    category: str
    description: str
    is_fee: bool = False
    fee_type: Optional[str] = None  # only meaningful when is_fee is True

    def to_dict(self) -> dict:
        return asdict(self)
