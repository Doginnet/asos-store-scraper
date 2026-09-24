import pytest
from src.extractors.asos import AsosExtractor
from config.categories import AsosCategory


@pytest.mark.live
def test_live_asos_catalog_fetch_limit_72_no_cookies():
    """
    Live Smoke Test:
    Tests real request to ASOS Search/Catalog API with limit=72 and without cookies,
    using curl_cffi Chrome 124 TLS impersonation and signature headers.
    """
    extractor = AsosExtractor()
    try:
        response = extractor.fetch_page(
            category_id=AsosCategory.TRAINERS,
            offset=0,
            limit=72
        )

        # Assertions
        assert response.itemCount > 0, f"Expected itemCount > 0, got {response.itemCount}"
        assert len(response.products) > 0, f"Expected products, got {len(response.products)}"
        
        # Verify page size: does ASOS return 72 items?
        print(f"\n[LIVE TEST] Total Category Items: {response.itemCount}")
        print(f"[LIVE TEST] Products returned on page 1 (limit=72): {len(response.products)}")

        first_product = response.products[0]
        assert first_product.id > 0
        assert len(first_product.name) > 0
        assert first_product.price.current > 0
        assert str(first_product.url).startswith("https://www.asos.com/")
        print(f"[LIVE TEST] Sample Product: {first_product.name} | Price: {first_product.price.current} {first_product.price.currency}")

    finally:
        extractor.close()
