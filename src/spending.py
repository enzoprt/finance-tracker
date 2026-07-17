"""Categorizes LCL/N26 spending transactions into everyday sub-categories,
and builds a monthly income/expense/net cash-flow report.

Sub-categorization is a simple keyword match on the transaction
description - approximate by nature (a personal tool, not a bank-grade
merchant classifier). Unmatched merchants fall into "other"; extend
SPENDING_KEYWORDS as new recurring merchants show up - this list covers
both everyday French spending and Canadian merchants (for the Quebec
exchange), since it's the single classifier used everywhere a spending
breakdown is shown, not one list per place/trip.
"""

from collections import defaultdict
from typing import List

from src.model import CATEGORY_INCOME, CATEGORY_SPENDING, Transaction

SPENDING_KEYWORDS = (
    ("LOYER", "rent"),
    ("RENT", "rent"),
    ("ASSURANCE", "insurance"),
    ("INSURANCE", "insurance"),
    ("HYDRO", "utilities"),
    ("ENERGIR", "utilities"),
    ("INTERNET", "phone_internet"),
    ("VIDEOTRON", "phone_internet"),
    ("BELL CANADA", "phone_internet"),
    ("FIDO", "phone_internet"),
    ("ROGERS", "phone_internet"),
    ("ORANGE", "phone_internet"),
    ("SFR", "phone_internet"),
    ("BOUYGUES", "phone_internet"),
    ("FREE MOBILE", "phone_internet"),
    ("CARREFOUR", "groceries"),
    ("LIDL", "groceries"),
    ("SUPECO", "groceries"),
    ("MONOPRIX", "groceries"),
    ("AUCHAN", "groceries"),
    ("IGA ", "groceries"),  # trailing space: "IGA" alone is too short/generic
    ("METRO", "groceries"),
    ("PROVIGO", "groceries"),
    ("SUPERC", "groceries"),
    ("MAXI ", "groceries"),  # trailing space avoids matching "Maxime" in a name
    ("COSTCO", "groceries"),
    ("ESCOTA", "transport"),
    ("TOTAL", "transport"),
    ("RELAIS PARC", "transport"),
    ("SNCF", "transport"),
    ("UBER", "transport"),
    ("STM ", "transport"),  # trailing space: "STM" alone is too short/generic
    ("OPUS ", "transport"),
    ("BIXI ", "transport"),
    ("EXO ", "transport"),  # trailing space avoids matching e.g. "exotique"
    ("BURGERKING", "dining"),
    ("BURGER KING", "dining"),
    ("MCDONALD", "dining"),
    ("TOOGOODTOGO", "dining"),
    ("TGTG", "dining"),
    ("TIM HORTONS", "dining"),
    ("RESTAURANT", "dining"),
    ("APPLE.COM", "subscriptions"),
    ("ITUNES", "subscriptions"),
    ("NETFLIX", "subscriptions"),
    ("SPOTIFY", "subscriptions"),
    ("CINEMA", "leisure"),
    ("CINEPLEX", "leisure"),
    ("SAQ ", "leisure"),  # trailing space: "SAQ" alone is too short/generic
    ("VINTED", "shopping"),
    ("LEBONCOIN", "shopping"),
    ("AMAZON", "shopping"),
    ("H&M", "shopping"),
    ("ZARA", "shopping"),
    ("SIMONS", "shopping"),
    ("COIFFURE", "personal_care"),
    ("PHARMACIE", "health"),
    ("PHARMACY", "health"),
    ("JEAN COUTU", "health"),
    ("SHOPPERS", "health"),
    ("AIR CANADA", "flights"),
    ("AIR TRANSAT", "flights"),
    ("AIRFRANCE", "flights"),
    ("AIR FRANCE", "flights"),
    ("PAYPAL", "online_payment"),
)


def spending_type_for(description: str) -> str:
    text_upper = description.upper()
    for keyword, category in SPENDING_KEYWORDS:
        if keyword in text_upper:
            return category
    return "other"


def build_cashflow_report(transactions: List[Transaction]) -> dict:
    relevant = [t for t in transactions if t.category in (CATEGORY_INCOME, CATEGORY_SPENDING)]

    by_month: dict = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    by_spending_type: dict = defaultdict(float)

    for t in relevant:
        month = t.date[:7]
        if t.category == CATEGORY_INCOME:
            by_month[month]["income"] += t.amount
        else:
            by_month[month]["expense"] += -t.amount
            by_spending_type[spending_type_for(t.description)] += -t.amount

    monthly = {}
    for month, values in sorted(by_month.items()):
        income = round(values["income"], 2)
        expense = round(values["expense"], 2)
        monthly[month] = {"income": income, "expense": expense, "net": round(income - expense, 2)}

    return {
        "monthly": monthly,
        "spending_by_type": {
            k: round(v, 2)
            for k, v in sorted(by_spending_type.items(), key=lambda kv: -kv[1])
        },
    }
