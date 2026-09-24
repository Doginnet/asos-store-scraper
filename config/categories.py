from enum import IntEnum
from typing import Dict, Any, Tuple, Optional


class AsosCategory(IntEnum):
    TRAINERS = 5775
    HOODIES = 5668
    T_SHIRTS = 7616
    JEANS = 4208
    JACKETS = 3606
    TROUSERS = 4910
    SHIRTS = 3602
    SWEATERS = 7617
    BOOTS = 5774
    ACCESSORIES = 4210


CATEGORY_REGISTRY: Dict[int, Dict[str, str]] = {
    AsosCategory.TRAINERS: {
        "slug": "trainers",
        "title": "Trainers & Sneakers",
        "description": "Men's athletic, retro, and lifestyle sneakers (Nike, adidas, New Balance, Salomon)"
    },
    AsosCategory.HOODIES: {
        "slug": "hoodies",
        "title": "Hoodies & Sweatshirts",
        "description": "Casual hoodies, oversized sweatshirts, and fleeces"
    },
    AsosCategory.T_SHIRTS: {
        "slug": "t-shirts",
        "title": "T-Shirts & Vests",
        "description": "Basic tees, graphic t-shirts, and branded streetwear tops"
    },
    AsosCategory.JEANS: {
        "slug": "jeans",
        "title": "Jeans",
        "description": "Denim pants: slim, baggy, straight, and cargo cuts"
    },
    AsosCategory.JACKETS: {
        "slug": "jackets",
        "title": "Jackets & Coats",
        "description": "Outerwear: puffers, trench coats, bombers, and windbreakers"
    },
    AsosCategory.TROUSERS: {
        "slug": "trousers",
        "title": "Trousers & Chinos",
        "description": "Smart trousers, casual chinos, and utility cargos"
    },
    AsosCategory.SHIRTS: {
        "slug": "shirts",
        "title": "Shirts",
        "description": "Casual overshirts, Oxford formal shirts, and printed short sleeves"
    },
    AsosCategory.SWEATERS: {
        "slug": "sweaters",
        "title": "Jumpers & Cardigans",
        "description": "Knitwear, crewneck jumpers, and textured cardigans"
    },
    AsosCategory.BOOTS: {
        "slug": "boots",
        "title": "Boots",
        "description": "Chelsea boots, combat boots, and hiking styles"
    },
    AsosCategory.ACCESSORIES: {
        "slug": "accessories",
        "title": "Accessories",
        "description": "Caps, beanies, bags, sunglasses, and belts"
    }
}


# Regional and store mapping
# ASOS uses specific store codes (ROE for Rest of Europe, COM for UK/Global, US for USA)
COUNTRY_STORE_MAP: Dict[str, Dict[str, str]] = {
    "BG": {"store": "ROE", "currency": "EUR"},
    "RO": {"store": "ROE", "currency": "EUR"},
    "PL": {"store": "ROE", "currency": "EUR"},
    "GR": {"store": "ROE", "currency": "EUR"},
    "DE": {"store": "ROE", "currency": "EUR"},
    "FR": {"store": "ROE", "currency": "EUR"},
    "ES": {"store": "ROE", "currency": "EUR"},
    "IT": {"store": "ROE", "currency": "EUR"},
    "NL": {"store": "ROE", "currency": "EUR"},
    "GB": {"store": "COM", "currency": "GBP"},
    "US": {"store": "COM", "currency": "USD"},
    "ROE": {"store": "ROE", "currency": "EUR"},
    "COM": {"store": "COM", "currency": "GBP"},
}


def resolve_store_and_currency(country: str = "BG", store: Optional[str] = None, currency: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Safely resolves country, store code, and currency to prevent ASOS 'No valid store was found' 400 errors.
    Ensures that (country, store, currency) are mutually compatible according to ASOS routing rules.
    """
    country_upper = (country or "BG").strip().upper()
    store_upper = store.strip().upper() if store else None

    # If country is mapped, use its store and currency as canonical baseline
    if country_upper in COUNTRY_STORE_MAP:
        mapping = COUNTRY_STORE_MAP[country_upper]
        canonical_store = mapping["store"]
        canonical_currency = mapping["currency"]

        # If user explicitly passed a store code, ensure cross-compatibility
        if store_upper in ("ROE", "COM"):
            if canonical_store != store_upper:
                # Resolve mismatch (e.g., store=COM with country=BG)
                if store_upper == "COM":
                    country_upper = "GB"
                    canonical_currency = "GBP"
                else:
                    country_upper = "BG"
                    canonical_currency = "EUR"
            resolved_store = store_upper
        else:
            resolved_store = canonical_store

        resolved_currency = currency.strip().upper() if currency else canonical_currency
    else:
        # Unknown country, fallback to Rest of Europe / EUR
        resolved_store = store_upper if store_upper in ("ROE", "COM") else "ROE"
        resolved_currency = currency.strip().upper() if currency else "EUR"

    return country_upper, resolved_store, resolved_currency
