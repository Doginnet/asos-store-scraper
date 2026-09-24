"""Unit tests for ASOS data models validation."""

import json
from pathlib import Path
import pytest
from src.models import AsosPrice, AsosProduct, AsosSearchResponse

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "search_sample.json"


@pytest.fixture
def raw_fixture_data() -> dict:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def search_response(raw_fixture_data: dict) -> AsosSearchResponse:
    return AsosSearchResponse.model_validate(raw_fixture_data)


@pytest.mark.unit
def test_search_response_counts(search_response: AsosSearchResponse) -> None:
    """Verify total item count and parsed products list length."""
    assert search_response.itemCount == 1233
    assert len(search_response.products) == 16


@pytest.mark.unit
def test_first_product_validation(search_response: AsosSearchResponse) -> None:
    """Verify first product (id: 205774480) attributes."""
    product = search_response.products[0]
    assert product.id == 205774480
    assert product.price.current == 110.0
    assert product.price.previous is None
    assert product.price.isMarkedDown is False
    assert product.price.discount_percent == 0.0


@pytest.mark.unit
def test_discounted_product_validation(search_response: AsosSearchResponse) -> None:
    """Verify discounted product (id: 210252768, Superstar II) attributes and discount calculation."""
    matches = [p for p in search_response.products if p.id == 210252768]
    assert len(matches) == 1
    product = matches[0]
    assert "Superstar II" in product.name
    assert product.price.current == 89.99
    assert product.price.previous == 120.0
    assert product.price.isMarkedDown is True
    assert product.price.discount_percent == 25.0


@pytest.mark.unit
def test_product_urls_normalization(search_response: AsosSearchResponse) -> None:
    """Verify absolute URLs for product url and imageUrl attributes."""
    for product in search_response.products:
        assert product.url.startswith("https://www.asos.com/"), f"Unexpected url: {product.url}"
        assert product.imageUrl.startswith("https://images.asos-media.com/"), f"Unexpected imageUrl: {product.imageUrl}"
        for additional_url in product.additionalImageUrls:
            assert additional_url.startswith("https://"), f"Unexpected additionalImageUrl: {additional_url}"


@pytest.mark.unit
def test_price_model_standalone() -> None:
    """Test standalone price parsing and discount computation logic."""
    raw_price_nested = {
        "current": {"value": 75.0, "text": "£75.00"},
        "previous": {"value": 100.0, "text": "£100.00"},
        "rrp": {"value": 120.0, "text": "£120.00"},
        "lowestPriceInLast30Days": {"value": 70.0, "text": "£70.00"},
        "isMarkedDown": True,
        "isOutletPrice": False,
        "currency": "GBP",
    }
    price = AsosPrice.model_validate(raw_price_nested)
    assert price.current == 75.0
    assert price.previous == 100.0
    assert price.rrp == 120.0
    assert price.lowestPriceInLast30Days == 70.0
    assert price.currency == "GBP"
    assert price.isMarkedDown is True
    assert price.discount_percent == 25.0

    # Test edge case: no discount when previous is smaller or equal
    price_no_discount = AsosPrice(current=100.0, previous=100.0)
    assert price_no_discount.discount_percent == 0.0

    price_increased = AsosPrice(current=120.0, previous=100.0)
    assert price_increased.discount_percent == 0.0


@pytest.mark.unit
def test_product_url_validator_variations() -> None:
    """Test URL normalization with different input formats."""
    prod = AsosProduct.model_validate({
        "id": 1,
        "name": "Test Item",
        "productCode": 100,
        "brandName": "Test Brand",
        "price": {"current": {"value": 10.0}},
        "url": "/test-item/prd/1",
        "imageUrl": "//images.asos-media.com/test.jpg",
        "additionalImageUrls": ["images.asos-media.com/extra1.jpg", "https://images.asos-media.com/extra2.jpg"],
    })
    assert prod.url == "https://www.asos.com/test-item/prd/1"
    assert prod.imageUrl == "https://images.asos-media.com/test.jpg"
    assert prod.additionalImageUrls == [
        "https://images.asos-media.com/extra1.jpg",
        "https://images.asos-media.com/extra2.jpg",
    ]


@pytest.mark.unit
def test_null_image_url_handling() -> None:
    """Ensure null/None/empty imageUrl parses without ValidationError."""
    prod = AsosProduct.model_validate({
        "id": 2,
        "name": "Placeholder Item",
        "productCode": 200,
        "brandName": "Brand",
        "price": {"current": {"value": 50.0}},
        "url": "/item/2",
        "imageUrl": None,
    })
    assert prod.imageUrl == ""


@pytest.mark.unit
def test_language_sanitization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure POSIX locales like en_US.UTF-8 from terminal environments are sanitized."""
    from config.settings import Settings
    from src.extractors.asos import AsosExtractor

    monkeypatch.setenv("LANG", "en_US.UTF-8")
    s = Settings()
    assert s.LANG == "en-GB"

    extractor = AsosExtractor(lang="en_US.UTF-8")
    assert extractor.lang == "en-GB"

