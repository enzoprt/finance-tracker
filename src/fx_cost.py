"""Detects foreign-currency card transactions and compares the exchange
rate actually applied against the ECB reference rate for that date
(frankfurter.app), to measure the real markup paid - e.g. for N26's
EUR-CAD conversions during the Quebec exchange semester.

Card transaction remittance text embeds the original foreign amount as
"XXX 99,99" (ISO currency code + comma-decimal amount) alongside the
merchant line; validated against real LCL card purchases in DKK/CHF/SEK
from a trip in April 2026. N26's exact wording for CAD transactions is
unconfirmed until real Quebec-period data exists - re-check this pattern
against the first real N26/CAD transaction.
"""

import re
from typing import List, Optional

from src.fx import get_rate
from src.model import Transaction

FOREIGN_AMOUNT_PATTERN = re.compile(r"\b([A-Z]{3})\s+(\d+(?:[.,]\d{2}))\b")


def _extract_foreign_amount(description: str, settlement_currency: str) -> Optional[dict]:
    for currency, amount_str in FOREIGN_AMOUNT_PATTERN.findall(description):
        if currency == settlement_currency:
            continue
        return {"currency": currency, "amount": float(amount_str.replace(",", "."))}
    return None


def analyze_foreign_transaction(date: str, eur_charged: float, description: str) -> Optional[dict]:
    """eur_charged: the actual EUR amount debited (positive)."""
    foreign = _extract_foreign_amount(description, "EUR")
    if foreign is None:
        return None

    ecb_rate = get_rate(foreign["currency"], "EUR", on_date=date)
    ecb_equivalent_eur = foreign["amount"] * ecb_rate
    markup_pct = (eur_charged - ecb_equivalent_eur) / ecb_equivalent_eur * 100

    return {
        "date": date,
        "foreign_currency": foreign["currency"],
        "foreign_amount": foreign["amount"],
        "eur_charged": eur_charged,
        "ecb_equivalent_eur": round(ecb_equivalent_eur, 4),
        "markup_pct": round(markup_pct, 2),
    }


def build_fx_cost_report(transactions: List[Transaction]) -> dict:
    results = []
    for t in transactions:
        if t.currency != "EUR" or t.amount >= 0:
            continue
        result = analyze_foreign_transaction(t.date, -t.amount, t.description)
        if result:
            result["account"] = t.account
            results.append(result)

    average_markup = (
        round(sum(r["markup_pct"] for r in results) / len(results), 2) if results else None
    )

    return {"transactions": results, "average_markup_pct": average_markup}
