import time
import random
from typing import Any, Dict, Generator, Optional
from loguru import logger

from config.settings import settings
from config.categories import resolve_store_and_currency
from src.core.client import ResilientHttpClient
from src.extractors.base import BaseExtractor


class AsosExtractor(BaseExtractor):
    """
    High-performance extractor for ASOS catalog using internal REST API.
    Handles pagination, query parameter construction, and raw/validated parsing.
    """

    SEARCH_ENDPOINT = f"{settings.BASE_URL}/api/product/search/v2/categories"

    def __init__(
        self,
        client: Optional[ResilientHttpClient] = None,
        store: Optional[str] = None,
        country: Optional[str] = None,
        currency: Optional[str] = None,
        lang: str = settings.LANG
    ):
        super().__init__(client=client)
        # Safely resolve country, store, and currency to prevent ASOS 400 errors
        resolved_country, resolved_store, resolved_currency = resolve_store_and_currency(
            country=country or settings.COUNTRY,
            store=store or settings.STORE_CODE,
            currency=currency or settings.CURRENCY
        )
        self.country = resolved_country
        self.store = resolved_store
        self.currency = resolved_currency
        self.lang = lang

        # Automatically sync store routing cookies into the HTTP client session
        self.sync_session_cookies()

    CURRENCY_ID_MAP: Dict[str, str] = {
        "EUR": "19",
        "GBP": "1",
        "USD": "2",
    }

    def sync_session_cookies(self) -> None:
        """
        Synchronizes store, country, and currency into session cookies.
        Uses verified Postman cookie set as base and updates store routing fields.
        """
        curr_id = self.CURRENCY_ID_MAP.get(self.currency, "19")
        cookie_payload = {
            **settings.DEFAULT_COOKIES,
            "storeCode": self.store,
            "browseCountry": self.country,
            "browseCurrency": self.currency,
            "geocountry": self.country,
            "currency": curr_id,
            "keyStoreDataversion": settings.KEYSTORE_DATAVERSION,
        }
        self.client.session.cookies.update(cookie_payload)

    def _build_params(self, offset: int, limit: int) -> Dict[str, Any]:
        return {
            "channel": "desktop-web",
            "country": self.country,
            "currency": self.currency,
            "keyStoreDataversion": settings.KEYSTORE_DATAVERSION,
            "lang": self.lang,
            "limit": limit,
            "offset": offset,
            "rowlength": 4,
            "store": self.store,
            "tstSearchSponsoredProducts": "true"
        }

    def fetch_page_raw(self, category_id: int, offset: int = 0, limit: int = settings.DEFAULT_LIMIT) -> Dict[str, Any]:
        """
        Fetches a single page of category results as raw JSON dictionary.
        Includes automatic session warm-up, cookie sync, and self-healing.
        """
        url = f"{self.SEARCH_ENDPOINT}/{category_id}"
        params = self._build_params(offset=offset, limit=limit)
        
        logger.info(f"Fetching ASOS category {category_id} | offset={offset} limit={limit} store={self.store} country={self.country}")
        response = self.client.get(url, params=params)
        
        # Self-healing: if store was rejected by Akamai, warm up edge session & sync store cookies
        if response.status_code == 400 and "No valid store was found" in response.text:
            logger.warning("ASOS returned 'No valid store was found'. Healing session: warming up edge cookies & re-routing...")
            self.store = "ROE"
            self.country = "BG"
            self.currency = "EUR"
            self.client.warmup()
            self.sync_session_cookies()
            params = self._build_params(offset=offset, limit=limit)
            response = self.client.get(url, params=params)

        if response.status_code != 200:
            raise RuntimeError(f"Unexpected status code {response.status_code}: {response.text[:200]}")
            
        return response.json()

    def fetch_page(self, category_id: int, offset: int = 0, limit: int = settings.DEFAULT_LIMIT) -> Any:
        """
        Fetches and validates a single page of products into Pydantic models.
        """
        from src.models.product import AsosSearchResponse
        raw_data = self.fetch_page_raw(category_id=category_id, offset=offset, limit=limit)
        return AsosSearchResponse.model_validate(raw_data)

    def iter_category(
        self,
        category_id: int,
        max_items: Optional[int] = None,
        limit: int = settings.DEFAULT_LIMIT,
        delay_range: tuple[float, float] = (0.5, 1.2)
    ) -> Generator[Any, None, None]:
        """
        Iterates over all products in a given category, automatically paginating with jitter.
        Yields AsosProduct instances.
        """
        offset = 0
        total_yielded = 0
        total_items = None

        while True:
            page_data = self.fetch_page(category_id=category_id, offset=offset, limit=limit)
            
            if total_items is None:
                total_items = page_data.itemCount
                logger.info(f"Category {category_id} contains total {total_items} items.")

            products = page_data.products
            if not products:
                logger.info("No more products returned by API. Reached end of catalog.")
                break

            for product in products:
                yield product
                total_yielded += 1
                if max_items and total_yielded >= max_items:
                    logger.info(f"Reached max requested items limit ({max_items}). Stopping.")
                    return

            offset += len(products)
            if offset >= total_items:
                logger.info(f"Completed pagination: gathered {total_yielded}/{total_items} items.")
                break

            # Polite randomized delay to avoid rate limiting
            sleep_time = random.uniform(*delay_range)
            time.sleep(sleep_time)
