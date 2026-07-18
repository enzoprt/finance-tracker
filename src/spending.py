"""Categorizes LCL/N26 spending transactions into a two-level category/
subcategory taxonomy, and builds a monthly income/expense/net cash-flow
report.

Sub-categorization is a simple keyword match on the transaction
description - approximate by nature (a personal tool, not a bank-grade
merchant classifier). Unmatched merchants fall into "other"; extend
SPENDING_KEYWORDS as new recurring merchants show up. The taxonomy itself
is deliberately broader than any single person's actual spending history
(it includes categories like education, gifts, and admin/taxes that may
never fire for a given user yet) - it's meant to hold up as spending
patterns change (e.g. moving out, starting a first job), not just
describe the past. Covers everyday French merchants and Canadian ones
(for the Quebec exchange) in the same list, since it's the single
classifier used everywhere a spending breakdown is shown.
"""

from collections import defaultdict
from typing import List, Optional, Tuple

from src.model import CATEGORY_INCOME, CATEGORY_SPENDING, Transaction

# (keyword, category, subcategory) - checked in order, first match wins,
# so more specific keywords (e.g. "ASSURANCE HABITATION") must come before
# generic fallbacks (bare "ASSURANCE") that would otherwise shadow them.
SPENDING_KEYWORDS: Tuple[Tuple[str, str, str], ...] = (
    # --- Housing ---
    ("LOYER", "housing", "rent"),
    ("RENT", "housing", "rent"),
    ("CHARGES LOCATIVES", "housing", "utilities"),
    ("ASSURANCE HABITATION", "housing", "home_insurance"),
    ("HOME INSURANCE", "housing", "home_insurance"),
    ("TENANT INSURANCE", "housing", "home_insurance"),
    ("HYDRO", "housing", "utilities"),
    ("ENERGIR", "housing", "utilities"),
    ("EDF", "housing", "utilities"),
    ("ENGIE", "housing", "utilities"),
    ("VEOLIA", "housing", "utilities"),
    ("IKEA", "housing", "furniture_home"),
    ("CONFORAMA", "housing", "furniture_home"),
    ("CASTORAMA", "housing", "maintenance_repairs"),
    ("LEROY MERLIN", "housing", "maintenance_repairs"),
    ("HOME DEPOT", "housing", "maintenance_repairs"),
    ("RONA", "housing", "maintenance_repairs"),
    # --- Phone & internet ---
    ("INTERNET", "phone_internet", "home_internet"),
    ("VIDEOTRON", "phone_internet", "home_internet"),
    ("BELL CANADA", "phone_internet", "mobile_plan"),
    ("FIDO", "phone_internet", "mobile_plan"),
    ("ROGERS", "phone_internet", "mobile_plan"),
    ("ORANGE", "phone_internet", "mobile_plan"),
    ("SFR", "phone_internet", "mobile_plan"),
    ("BOUYGUES", "phone_internet", "mobile_plan"),
    ("FREE MOBILE", "phone_internet", "mobile_plan"),
    # --- Groceries ---
    ("CARREFOUR", "groceries", "supermarket"),
    ("LIDL", "groceries", "supermarket"),
    ("SUPECO", "groceries", "supermarket"),
    ("MONOPRIX", "groceries", "supermarket"),
    ("AUCHAN", "groceries", "supermarket"),
    ("IGA ", "groceries", "supermarket"),  # trailing space: "IGA" alone is too short/generic
    ("METRO", "groceries", "supermarket"),
    ("PROVIGO", "groceries", "supermarket"),
    ("SUPERC", "groceries", "supermarket"),
    ("MAXI ", "groceries", "supermarket"),  # trailing space avoids matching "Maxime" in a name
    ("COSTCO", "groceries", "supermarket"),
    ("NETTO ", "groceries", "supermarket"),  # trailing space avoids matching "nettoyage"
    ("FOETEX", "groceries", "supermarket"),
    ("7-ELEVEN", "groceries", "supermarket"),
    ("BIOCOOP", "groceries", "specialty_food"),
    ("NATURALIA", "groceries", "specialty_food"),
    ("BOULANGERIE", "groceries", "specialty_food"),
    ("FROMAGERIE", "groceries", "specialty_food"),
    ("PRIMEUR", "groceries", "specialty_food"),
    # --- Dining ---
    ("BURGERKING", "dining", "fast_food"),
    ("BURGER KING", "dining", "fast_food"),
    ("MCDONALD", "dining", "fast_food"),
    ("TIM HORTONS", "dining", "fast_food"),
    ("KFC", "dining", "fast_food"),
    ("SUBWAY", "dining", "fast_food"),
    ("TOOGOODTOGO", "dining", "restaurants"),
    ("TGTG", "dining", "restaurants"),
    ("RESTAURANT", "dining", "restaurants"),
    ("UBER EATS", "dining", "delivery"),
    ("UBEREATS", "dining", "delivery"),
    ("DELIVEROO", "dining", "delivery"),
    ("DOORDASH", "dining", "delivery"),
    ("SKIPTHEDISHES", "dining", "delivery"),
    ("STARBUCKS", "dining", "cafes_bars"),
    ("TIM HORTON", "dining", "cafes_bars"),
    ("SAQ ", "dining", "cafes_bars"),  # trailing space: "SAQ" alone is too short/generic - Quebec liquor board
    ("CAVE A VIN", "dining", "cafes_bars"),
    ("BAR ", "dining", "cafes_bars"),
    # --- Health ---
    ("MUTUELLE", "health", "health_insurance"),
    ("ASSURANCE SANTE", "health", "health_insurance"),
    ("ASSURANCE MALADIE", "health", "health_insurance"),
    ("HEALTH INSURANCE", "health", "health_insurance"),
    ("PHARMACIE", "health", "pharmacy"),
    ("PHARMACY", "health", "pharmacy"),
    ("JEAN COUTU", "health", "pharmacy"),
    ("SHOPPERS", "health", "pharmacy"),
    ("DENTISTE", "health", "doctor_dental"),
    ("DENTIST", "health", "doctor_dental"),
    ("CABINET MEDICAL", "health", "doctor_dental"),
    ("CLINIQUE", "health", "doctor_dental"),
    ("BASIC FIT", "health", "fitness_sports"),
    ("BASIC-FIT", "health", "fitness_sports"),
    ("FITNESS", "health", "fitness_sports"),
    ("PISCINE", "health", "fitness_sports"),
    # --- Personal care & shopping ---
    ("COIFFURE", "personal_care", "haircut_grooming"),
    ("BARBER", "personal_care", "haircut_grooming"),
    ("SEPHORA", "personal_care", "cosmetics_hygiene"),
    ("NOCIBE", "personal_care", "cosmetics_hygiene"),
    ("VINTED", "shopping", "online_marketplace"),
    ("LEBONCOIN", "shopping", "online_marketplace"),
    ("AMAZON", "shopping", "online_marketplace"),
    ("EBAY", "shopping", "online_marketplace"),
    ("H&M", "shopping", "clothing"),
    ("ZARA", "shopping", "clothing"),
    ("SIMONS", "shopping", "clothing"),
    ("UNIQLO", "shopping", "clothing"),
    ("DECATHLON", "shopping", "clothing"),
    ("FNAC", "shopping", "electronics"),
    ("DARTY", "shopping", "electronics"),
    ("APPLE STORE", "shopping", "electronics"),
    ("BEST BUY", "shopping", "electronics"),
    # --- Subscriptions ---
    ("APPLE.COM", "subscriptions", "software_cloud"),
    (" APPLE ", "subscriptions", "software_cloud"),  # spaces both sides: standalone word only, e.g. "CB APPLE 19/06/26" - avoids "pineapple" etc.
    ("ITUNES", "subscriptions", "streaming"),
    ("NETFLIX", "subscriptions", "streaming"),
    ("SPOTIFY", "subscriptions", "streaming"),
    ("DISNEY", "subscriptions", "streaming"),
    ("YOUTUBE PREMIUM", "subscriptions", "streaming"),
    ("ICLOUD", "subscriptions", "software_cloud"),
    ("GOOGLE ONE", "subscriptions", "software_cloud"),
    ("MICROSOFT 365", "subscriptions", "software_cloud"),
    ("ADOBE", "subscriptions", "software_cloud"),
    # --- Transport ---
    ("AIR CANADA", "transport", "flights"),
    ("AIR TRANSAT", "transport", "flights"),
    ("AIRFRANCE", "transport", "flights"),
    ("AIR FRANCE", "transport", "flights"),
    ("EASYJET", "transport", "flights"),
    ("RYANAIR", "transport", "flights"),
    ("SNCF", "transport", "train"),
    ("VIA RAIL", "transport", "train"),
    ("TRAINLINE", "transport", "train"),
    ("STM ", "transport", "public_transit"),  # trailing space: "STM" alone is too short/generic
    ("REJSEKORT", "transport", "public_transit"),
    ("OPUS ", "transport", "public_transit"),
    ("EXO ", "transport", "public_transit"),  # trailing space avoids matching e.g. "exotique"
    ("RATP", "transport", "public_transit"),
    ("UBER", "transport", "rideshare_taxi"),
    ("LYFT", "transport", "rideshare_taxi"),
    ("TAXI", "transport", "rideshare_taxi"),
    ("BIXI ", "transport", "bike"),
    ("VELIB", "transport", "bike"),
    ("ESCOTA", "transport", "parking_tolls"),
    ("PARKING", "transport", "parking_tolls"),
    ("RELAIS PARC", "transport", "gas_fuel"),  # a highway service-station chain despite the name - not parking (real charges: 21-71EUR, recurring)
    ("TOTAL", "transport", "gas_fuel"),
    ("ESSO", "transport", "gas_fuel"),
    ("SHELL", "transport", "gas_fuel"),
    ("PETRO-CANADA", "transport", "gas_fuel"),
    ("AVIS", "transport", "car_rental"),
    ("HERTZ", "transport", "car_rental"),
    ("ENTERPRISE", "transport", "car_rental"),
    ("ASSURANCE AUTO", "transport", "car_insurance"),
    ("ASSURANCE VOITURE", "transport", "car_insurance"),
    ("CAR INSURANCE", "transport", "car_insurance"),
    # --- Leisure ---
    ("AIRBNB", "leisure", "lodging_travel"),
    ("BOOKING.COM", "leisure", "lodging_travel"),
    ("HOTEL", "leisure", "lodging_travel"),
    ("CINEMA", "leisure", "events_entertainment"),
    ("CINEPLEX", "leisure", "events_entertainment"),
    ("TICKETMASTER", "leisure", "events_entertainment"),
    ("CONCERT", "leisure", "events_entertainment"),
    ("MUSEE", "leisure", "events_entertainment"),
    ("MUSEUM", "leisure", "events_entertainment"),
    ("STEAM", "leisure", "books_games"),
    ("KINGUIN", "leisure", "books_games"),
    ("PLAYSTATION", "leisure", "books_games"),
    ("NINTENDO", "leisure", "books_games"),
    ("LIBRAIRIE", "leisure", "books_games"),
    # --- Education ---
    ("UNIVERSITE", "education", "tuition"),
    ("UNIVERSITY", "education", "tuition"),
    ("SCOLARITE", "education", "tuition"),
    ("TUITION", "education", "tuition"),
    ("FOURNITURES SCOLAIRES", "education", "books_supplies"),
    ("UDEMY", "education", "courses"),
    ("COURSERA", "education", "courses"),
    # --- Gifts & donations ---
    ("CADEAU", "gifts_donations", "gifts"),
    ("GIFT", "gifts_donations", "gifts"),
    ("DON A", "gifts_donations", "donations"),
    ("DONATION", "gifts_donations", "donations"),
    ("UNICEF", "gifts_donations", "donations"),
    # --- Admin & taxes ---
    ("IMPOTS", "admin_taxes", "taxes"),
    ("IMPOT SUR", "admin_taxes", "taxes"),
    ("TAXE", "admin_taxes", "taxes"),  # e.g. "taxe fonciere" - "TAX " (with space) would miss this
    ("PREFECTURE", "admin_taxes", "government_fees"),
    ("NOTAIRE", "admin_taxes", "legal_notary"),
    # --- Generic insurance fallback (kept last among insurance keywords so
    #     the more specific health/home/car ones above take priority) ---
    ("ASSURANCE", "housing", "home_insurance"),
    ("INSURANCE", "housing", "home_insurance"),
    # --- Online payment pass-through (merchant behind PayPal not visible) ---
    ("PAYPAL", "online_payment", None),
)


def spending_type_for(description: str) -> str:
    """Top-level category only (e.g. "transport") - unchanged signature,
    used wherever only the coarse breakdown matters."""
    category, _ = spending_subtype_for(description)
    return category


def spending_subtype_for(description: str) -> Tuple[str, str]:
    """(category, subcategory) - subcategory is "other" when the keyword
    has none (e.g. PayPal, whose actual merchant is never visible) or when
    nothing matched at all."""
    text_upper = description.upper()
    for keyword, category, subcategory in SPENDING_KEYWORDS:
        if keyword in text_upper:
            return category, subcategory or "other"
    return "other", "other"


# Clean display names for keywords whose raw form is a poor label (e.g.
# "NETFLIX" is fine as-is, but "APPLE.COM"/"ITUNES" read oddly verbatim).
# Only keywords worth surfacing by name (mainly subscriptions) are listed;
# everything else falls back to a title-cased version of the keyword.
MERCHANT_LABELS = {
    "NETFLIX": "Netflix",
    "SPOTIFY": "Spotify",
    "APPLE.COM": "Apple",
    "ITUNES": "Apple (iTunes/App Store)",
    "DISNEY": "Disney+",
    "YOUTUBE PREMIUM": "YouTube Premium",
    "ICLOUD": "iCloud",
    "GOOGLE ONE": "Google One",
    "MICROSOFT 365": "Microsoft 365",
    "ADOBE": "Adobe",
}


def merchant_for(description: str) -> Optional[str]:
    """Best-effort clean display name for the merchant that matched (e.g.
    "Netflix" rather than the raw "NETFLIX.COM" substring) - used to list
    subscriptions by name. None if nothing matched."""
    text_upper = description.upper()
    for keyword, _category, _subcategory in SPENDING_KEYWORDS:
        if keyword in text_upper:
            return MERCHANT_LABELS.get(keyword, keyword.strip().title())
    return None


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
